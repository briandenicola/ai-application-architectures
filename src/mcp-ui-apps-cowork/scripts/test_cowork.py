import json
from pathlib import Path
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
            "tenant_id": "tenant", "oauth_client_id": "client",
            "oauth_scope": "api://gateway/access_as_user",
        }

    def test_connector_reconfiguration_preserves_only_matching_oauth_registration(self):
        cowork.configure(self.values, self.path)
        with self.path.open("a") as file:
            file.write("OAUTH_CONFIG_ID=registered\n")
        cowork.configure(self.values, self.path)
        self.assertEqual(cowork.read_env(self.path)["OAUTH_CONFIG_ID"], "registered")
        cowork.configure({**self.values, "oauth_client_id": "replacement"}, self.path)
        self.assertNotIn("OAUTH_CONFIG_ID", cowork.read_env(self.path))

    def test_package_requires_oauth_and_contains_skill_icons_and_remote_connector(self):
        with self.assertRaisesRegex(ValueError, "OAUTH_CONFIG_ID"):
            cowork.manifest(self.values, "")
        build = Path(self.directory.name) / "build"
        with patch.object(cowork, "BUILD", build), patch.object(cowork, "read_env",
                                                             return_value={"OAUTH_CONFIG_ID": "registered"}):
            cowork.package_plugin(self.values)
        with zipfile.ZipFile(build / "banking-cowork.zip") as archive:
            manifest = json.loads(archive.read("manifest.json"))
            connector = manifest["agentConnectors"][0]["toolSource"]["remoteMcpServer"]
            self.assertEqual(connector["mcpServerUrl"], self.values["mcp_url"])
            self.assertEqual(connector["authorization"],
                             {"type": "OAuthPluginVault", "referenceId": "registered"})
            self.assertIn("PENDING_APPROVAL", archive.read("skills/wire-review/SKILL.md").decode())
            for name in ("color.png", "outline.png"):
                self.assertTrue(archive.read(name).startswith(b"\x89PNG\r\n\x1a\n"))

    def test_package_command_rejects_registration_for_a_changed_connector(self):
        root = Path(self.directory.name)
        path = root / "cowork" / "env" / ".env.local"
        cowork.configure(self.values, path)
        with path.open("a") as file:
            file.write("OAUTH_CONFIG_ID=registered\n")
        replacement = {**self.values, "oauth_client_id": "replacement"}
        with patch.object(cowork, "ROOT", root), patch.object(cowork, "settings", return_value=replacement), \
                patch("sys.argv", ["cowork.py", "package"]):
            with self.assertRaisesRegex(ValueError, "OAUTH_CONFIG_ID"):
                cowork.main()
        self.assertNotIn("OAUTH_CONFIG_ID", cowork.read_env(path))


if __name__ == "__main__":
    unittest.main()
