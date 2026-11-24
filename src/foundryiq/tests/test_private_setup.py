import base64
import gzip
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError

from scripts import demo, runner_bootstrap


class PrivateConfigurationTests(unittest.TestCase):
    def test_operator_uses_cli_token_identity_not_terraform_credentials(self):
        oid = "00000000-0000-0000-0000-000000000001"
        encoded = base64.urlsafe_b64encode(json.dumps({"oid": oid}).encode()).decode().rstrip("=")
        with (
            patch.dict(os.environ, {"AZURE_SUBSCRIPTION_ID": "subscription"}, clear=True),
            patch.object(demo.AzureRest, "token", return_value=f"header.{encoded}.signature"),
        ):
            self.assertEqual(demo.operator_object_id(), oid)

    def test_private_runner_accepts_basic_but_rejects_free_and_invalid_network_ranges(self):
        with patch.dict(
            os.environ,
            {"TF_VAR_search_sku": "basic", "TF_VAR_network_address_space": "10.88.0.0/16"},
            clear=True,
        ):
            demo.verify_private_configuration()
        for changes, message in [
            ({"TF_VAR_search_sku": "free"}, "billable"),
            ({"TF_VAR_network_address_space": ""}, "IPv4"),
            ({"TF_VAR_network_address_space": "10.88.0.0/27"}, "two /27"),
        ]:
            environment = {
                "TF_VAR_search_sku": "basic",
                "TF_VAR_network_address_space": "10.88.0.0/16",
                **changes,
            }
            with (
                self.subTest(changes=changes),
                patch.dict(os.environ, environment, clear=True),
                self.assertRaisesRegex(RuntimeError, message),
            ):
                demo.verify_private_configuration()

    def test_worker_requires_exclusively_the_configured_private_endpoint(self):
        config = {"storage_account": "synthetic", "storage_private_ip": "10.88.0.36"}
        for addresses in [
            ["10.88.0.36"],
            ["192.0.2.1"],
            ["10.88.0.36", "192.0.2.1"],
        ]:
            results = [(socket.AF_INET, 0, 0, "", (address, 443)) for address in addresses]
            with (
                self.subTest(addresses=addresses),
                patch.object(demo.socket, "getaddrinfo", return_value=results),
            ):
                if addresses == ["10.88.0.36"]:
                    demo.verify_private_storage(config)
                else:
                    with self.assertRaisesRegex(RuntimeError, "private DNS"):
                        demo.verify_private_storage(config)

    def test_blob_network_denial_fails_without_propagation_retries(self):
        url = "https://synthetic.blob.core.windows.net/handbook/policy.md"
        errors = [
            HTTPError(
                url,
                403,
                "Forbidden",
                {"x-ms-error-code": "AuthorizationFailure"},
                io.BytesIO(b"<Error><Code>AuthorizationFailure</Code></Error>"),
            )
            for _ in range(2)
        ]
        client = demo.AzureRest("subscription")
        client.token = Mock(return_value="synthetic-token")
        with (
            patch.object(demo, "urlopen", side_effect=errors) as send,
            patch.object(demo.time, "monotonic", side_effect=[0, 1, 301]),
            patch.object(demo.time, "sleep") as sleep,
            self.assertRaisesRegex(demo.ServiceError, "network access is blocked"),
        ):
            client.request("PUT", url, demo.STORAGE_AUDIENCE, b"policy", propagation=True)
        send.assert_called_once()
        sleep.assert_not_called()


class PrivateJobTests(unittest.TestCase):
    def setUp(self):
        connection = patch.object(demo, "connect_telemetry")
        self.connect = connection.start()
        self.addCleanup(connection.stop)

    def config(self):
        return {
            "subscription_id": "subscription",
            "resource_group": "synthetic-group",
            "search_index": "handbook-index",
            "setup_runner_id": "/subscriptions/s/providers/Microsoft.App/jobs/setup",
            "setup_runner_name": "setup",
            "setup_runner_image": "mcr.microsoft.com/azure-cli:synthetic",
            "setup_runner_client_id": "synthetic-managed-identity",
            "application_insights_id": "/subscriptions/s/components/insights",
            "application_insights_app_id": "synthetic-application",
        }

    def test_job_status_controls_success_and_failure(self):
        for status in ("Succeeded", "Failed", "Stopped"):
            self.connect.reset_mock()
            config = self.config()
            client = Mock()
            client.request.side_effect = [
                {"value": []},
                {"properties": {"status": status}},
            ]

            def start(args, config=config, client=client):
                self.connect.assert_called_once_with(client, config)
                self.assertEqual(args[1:4], ["containerapp", "job", "start"])
                template = json.loads(Path(args[args.index("--yaml") + 1]).read_text())
                container = template["containers"][0]
                bundle = json.loads(gzip.decompress(base64.b64decode(container["args"][0])))
                self.assertEqual(bundle["config"], config)
                self.assertIn("scripts/demo.py", bundle["files"])
                return {"name": "setup-execution"}

            with (
                self.subTest(status=status),
                patch.object(demo, "command_json", side_effect=start),
                patch.object(demo, "show_runner_logs") as logs,
            ):
                if status == "Succeeded":
                    demo.private_setup(client, config)
                else:
                    with self.assertRaisesRegex(RuntimeError, status):
                        demo.private_setup(client, config)
                logs.assert_called_once_with(config, "setup-execution")

    def test_existing_execution_prevents_another_start(self):
        for later_page in (False, True):

            def request(method, url, audience, later_page=later_page):
                if later_page and url.endswith(f"/executions?api-version={demo.JOB_API}"):
                    return {"value": [], "nextLink": "https://management.azure.com/next"}
                return {
                    "value": [{"name": "existing", "properties": {"status": "Running"}}],
                    "properties": {"status": "Succeeded"},
                }

            client = Mock()
            client.request.side_effect = request
            with (
                self.subTest(later_page=later_page),
                patch.object(demo, "command_json", return_value={"name": "new"}) as start,
                patch.object(demo, "show_runner_logs"),
                self.assertRaisesRegex(RuntimeError, "already active"),
            ):
                demo.private_setup(client, self.config())
            start.assert_not_called()
            self.connect.assert_not_called()

    def test_legacy_state_requires_provisioning_before_setup(self):
        client = Mock()
        client.request.return_value = {"value": [], "properties": {"status": "Succeeded"}}
        config = {**self.config(), "setup_runner_id": ""}
        with (
            patch.object(demo, "command_json", return_value={"name": "execution"}),
            patch.object(demo, "show_runner_logs"),
            self.assertRaisesRegex(RuntimeError, "task up"),
        ):
            demo.private_setup(client, config)
        client.request.assert_not_called()

    def test_running_job_times_out_instead_of_reporting_success(self):
        client = Mock()
        client.request.return_value = {"value": [], "properties": {"status": "Running"}}
        with (
            patch.object(demo, "command_json", return_value={"name": "execution"}),
            patch.object(demo, "show_runner_logs") as logs,
            patch.object(demo.time, "monotonic", side_effect=[0, 1, 2401]),
            patch.object(demo.time, "sleep"),
            self.assertRaisesRegex(RuntimeError, "40 minutes"),
        ):
            demo.private_setup(client, self.config())
        logs.assert_called_once()

    def test_bundle_excludes_local_credentials_and_terraform_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            (root / "scripts/demo.py").write_text("print('synthetic worker')\n")
            (root / "scripts/telemetry.py").write_text("# Synthetic telemetry helper\n")
            (root / "data").mkdir()
            (root / "data/policy.md").write_text("Synthetic policy")
            (root / ".env").write_text("secret-placeholder")
            (root / "terraform.tfstate").write_text("secret-placeholder")
            with patch.object(demo, "ROOT", root):
                bundle = gzip.decompress(base64.b64decode(demo.runner_payload(self.config())))
            self.assertNotIn(b"secret-placeholder", bundle)
            self.assertEqual(
                set(json.loads(bundle)["files"]),
                {"scripts/demo.py", "scripts/telemetry.py", "data/policy.md"},
            )

    def test_real_worker_bundle_imports_without_runtime_packages(self):
        bundle = json.loads(gzip.decompress(base64.b64decode(demo.runner_payload(self.config()))))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, content in bundle["files"].items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
            result = subprocess.run(
                [sys.executable, str(root / "scripts/demo.py"), "--help"],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("worker", result.stdout)

    def test_empty_policy_bundle_cannot_start_a_demo(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            (root / "scripts/demo.py").write_text("print('synthetic')\n")
            (root / "scripts/telemetry.py").write_text("# Synthetic telemetry helper\n")
            with (
                patch.object(demo, "ROOT", root),
                self.assertRaisesRegex(RuntimeError, "No policy documents"),
            ):
                demo.runner_payload(self.config())

    def test_bootstrap_logs_in_with_managed_identity_and_preserves_worker_exit_code(self):
        bundle = {
            "config": self.config(),
            "files": {"scripts/demo.py": "print('synthetic')", "data/policy.md": "Synthetic"},
        }
        encoded = base64.b64encode(gzip.compress(json.dumps(bundle).encode())).decode()

        def run(args, **kwargs):
            if args[0] == "az":
                self.assertEqual(
                    args[1:5], ["login", "--identity", "--client-id", "synthetic-managed-identity"]
                )
                return Mock(returncode=0)
            self.assertEqual(args[-1], "worker")
            root = kwargs["cwd"]
            self.assertTrue((root / "data/policy.md").exists())
            self.assertEqual(json.loads(kwargs["env"]["DEMO_CONFIGURATION"]), self.config())
            return Mock(returncode=7)

        with (
            patch.object(runner_bootstrap.sys, "argv", ["bootstrap", encoded]),
            patch.object(runner_bootstrap.subprocess, "run", side_effect=run),
        ):
            self.assertEqual(runner_bootstrap.main(), 7)

    def test_local_setup_dispatches_to_job_not_local_blob_uploads(self):
        with (
            patch.object(demo.sys, "argv", ["demo", "setup"]),
            patch.object(demo, "configuration", return_value=self.config()),
            patch.object(demo, "private_setup") as private,
            patch.object(demo, "setup") as direct,
        ):
            self.assertEqual(demo.main(), 0)
        private.assert_called_once()
        direct.assert_not_called()

    def test_worker_uses_supplied_configuration_without_terraform(self):
        with (
            patch.object(demo.sys, "argv", ["demo", "worker"]),
            patch.dict(os.environ, {"DEMO_CONFIGURATION": json.dumps(self.config())}),
            patch.object(demo, "verify_private_storage") as private_dns,
            patch.object(demo, "configuration") as terraform,
            patch.object(demo, "setup") as direct,
        ):
            self.assertEqual(demo.main(), 0)
        terraform.assert_not_called()
        private_dns.assert_called_once_with(self.config())
        direct.assert_called_once()
