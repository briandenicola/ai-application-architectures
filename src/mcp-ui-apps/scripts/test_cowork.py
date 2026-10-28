import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import cowork


class CoworkPackagingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / ".env.local"
        self.values = {
            "plugin_id": "00000000-0000-4000-8000-000000000001",
            "mcp_url": "https://example.azurewebsites.net/mcp",
        }

    def test_connector_configuration_discards_stale_oauth_settings(self):
        self.path.write_text("OAUTH_CONFIG_ID=old-registration\nOAUTH_CLIENT_ID=old-client\n")
        cowork.configure(self.values, self.path)
        self.assertEqual(self.path.read_text(), f"PLUGIN_ID={self.values['plugin_id']}\nMCP_URL={self.values['mcp_url']}\n")

    def test_package_without_oauth_contains_skill_icons_and_anonymous_remote_connector(self):
        build = Path(self.directory.name) / "build"
        with patch.object(cowork, "BUILD", build):
            cowork.package_plugin(self.values)
        with zipfile.ZipFile(build / "banking-cowork.zip") as archive:
            manifest = json.loads(archive.read("manifest.json"))
            connector = manifest["agentConnectors"][0]["toolSource"]["remoteMcpServer"]
            self.assertEqual(connector["mcpServerUrl"], self.values["mcp_url"])
            self.assertEqual(connector["authorization"], {"type": "None"})
            self.assertIn("PENDING_APPROVAL", archive.read("skills/wire-review/SKILL.md").decode())
            for name in ("color.png", "outline.png"):
                self.assertTrue(archive.read(name).startswith(b"\x89PNG\r\n\x1a\n"))

    def test_agent_deployment_creates_versions_on_first_and_repeated_runs(self):
        values = {
            "project_endpoint": "https://example.services.ai.azure.com/api/projects/demo",
            "agent_name": "wire-investigator-demo", "model_deployment": "demo-model",
        }
        definitions = []

        def register(*args):
            self.assertEqual(args[:4], ("az", "rest", "--method", "post"))
            self.assertEqual(args[args.index("--url") + 1],
                             f"{values['project_endpoint']}/agents/{values['agent_name']}/versions?api-version=v1")
            self.assertEqual(args[args.index("--resource") + 1], "https://ai.azure.com")
            path = Path(args[args.index("--body") + 1].removeprefix("@"))
            definitions.append(json.loads(path.read_text(encoding="utf-8")))
            return json.dumps({"name": values["agent_name"], "version": str(len(definitions))})

        with patch.object(cowork, "BUILD", Path(self.directory.name) / "build"), \
                patch.object(cowork, "run", side_effect=register) as command:
            cowork.deploy_agent(values)
            cowork.deploy_agent(values)
        self.assertEqual(command.call_count, 2)
        for payload in definitions:
            self.assertEqual(payload["definition"], {
                "kind": "prompt", "model": values["model_deployment"],
                "instructions": (cowork.ROOT / "agent" / "wire-investigator.txt").read_text(encoding="utf-8"),
            })

    def test_build_stages_the_existing_functions_and_ui_without_zip_or_local_install(self):
        root = Path(self.directory.name)
        server = root / "mcp-server"
        (server / "dist").mkdir(parents=True)
        (server / "functions").mkdir()
        (server / "dist" / "wire-review.html").write_text("<html>banking panel</html>")
        package = {"type": "module", "scripts": {"start": "local"}, "dependencies": {"@azure/functions": "^4.7.2"}}
        (server / "package.json").write_text(json.dumps(package))
        (server / "package-lock.json").write_text('{"lockfileVersion":3}')
        for name in ("host.json", "Dockerfile", ".dockerignore"):
            shutil.copyfile(cowork.ROOT / "mcp-server" / "functions" / name, server / "functions" / name)
        build = root / "build"

        def bundle(*args, cwd):
            self.assertEqual(args[1], "functions/index.ts")
            output = Path(next(arg.removeprefix("--outfile=") for arg in args if arg.startswith("--outfile=")))
            output.parent.mkdir(parents=True)
            output.write_text("// bundled handlers")

        with patch.object(cowork, "ROOT", root), patch.object(cowork, "BUILD", build), \
                patch.object(cowork, "run", side_effect=bundle) as command:
            cowork.build_functions()
        self.assertEqual(command.call_count, 1)
        context = build / "functions"
        deployed_package = json.loads((context / "package.json").read_text())
        self.assertEqual(deployed_package["main"], "dist/index.js")
        self.assertNotIn("scripts", deployed_package)
        self.assertEqual(deployed_package["dependencies"], package["dependencies"])
        self.assertEqual((context / "dist" / "wire-review.html").read_text(), "<html>banking panel</html>")
        self.assertTrue((context / "Dockerfile").is_file())
        self.assertTrue((context / ".dockerignore").is_file())
        self.assertFalse((context / "node_modules").exists())
        self.assertFalse((build / "banking-functions.zip").exists())

    def test_publish_builds_once_and_records_an_immutable_image_for_both_apps(self):
        root = Path(self.directory.name)
        (root / "infra").mkdir()
        context = root / "build" / "functions"
        context.mkdir(parents=True)
        (context / "Dockerfile").write_text("FROM scratch\n")
        values = {"registry_name": "crdemo", "registry_server": "crdemo.azurecr.io"}
        digest = "sha256:" + "a" * 64

        def publish(command, *, cwd, check):
            dockerfile = (Path(command[command.index("--file") + 1]) if "--file" in command
                          else Path(command[-1]) / "Dockerfile")
            if not dockerfile.is_absolute():
                dockerfile = cwd / dockerfile
            self.assertEqual(dockerfile.read_text(), "FROM scratch\n")

        with patch.object(cowork, "ROOT", root), patch.object(cowork, "BUILD", root / "build"), \
                patch.object(cowork.subprocess, "run", side_effect=publish) as build, \
                patch.object(cowork, "run", return_value=digest) as lookup:
            cowork.deploy_functions(values)
        command = build.call_args.args[0]
        self.assertEqual(command[:3], ["az", "acr", "build"])
        self.assertEqual(command[command.index("--platform") + 1], "linux/amd64")
        self.assertEqual(command[-1], str(root / "build" / "functions"))
        tag = command[command.index("--image") + 1]
        lookup.assert_called_once_with(
            "az", "acr", "repository", "show", "--name", "crdemo",
            "--image", tag, "--query", "digest", "--output", "tsv",
        )
        self.assertEqual(json.loads((root / "infra" / "cowork.auto.tfvars.json").read_text()),
                         {"function_image": f"crdemo.azurecr.io/banking-functions@{digest}"})

    def test_failed_build_or_missing_digest_does_not_replace_the_last_deployment(self):
        root = Path(self.directory.name)
        (root / "infra").mkdir()
        path = root / "infra" / "cowork.auto.tfvars.json"
        path.write_text('{"function_image":"previous"}')
        values = {"registry_name": "crdemo", "registry_server": "crdemo.azurecr.io"}
        for failure in ("build", "digest"):
            with self.subTest(failure=failure), patch.object(cowork, "ROOT", root), \
                    patch.object(cowork.subprocess, "run",
                                 side_effect=subprocess.CalledProcessError(1, ["az", "acr", "build"])
                                 if failure == "build" else None), \
                    patch.object(cowork, "run", return_value=""):
                with self.assertRaises(subprocess.CalledProcessError if failure == "build" else ValueError):
                    cowork.deploy_functions(values)
                self.assertEqual(path.read_text(), '{"function_image":"previous"}')

    def test_read_only_verification_uses_anonymous_requests_without_azure_cli(self):
        methods = []

        def respond(request, timeout):
            self.assertIsNone(request.get_header("Authorization"))
            operation = json.loads(request.data)
            method = operation["method"]
            methods.append(method)
            payload = {
                "initialize": {},
                "tools/list": {"tools": [
                    {"name": "get_high_risk_wires"}, {"name": "analyze_wire"},
                    {"name": "create_hold_request", "_meta": {"ui": {"visibility": ["app"]}}},
                ]},
                "tools/call": {"structuredContent": {"wires": [{}, {}, {}]}},
                "resources/read": {"contents": [{"mimeType": "text/html;profile=mcp-app"}]},
            }[method]
            return io.BytesIO(json.dumps({"jsonrpc": "2.0", "id": operation["id"], "result": payload}).encode())

        with patch.object(cowork, "urlopen", side_effect=respond), \
                patch.object(cowork, "run", side_effect=AssertionError("Anonymous verification must not invoke Azure CLI")):
            cowork.verify(self.values)
        self.assertEqual(methods, ["initialize", "tools/list", "tools/call", "resources/read"])


if __name__ == "__main__":
    unittest.main()
