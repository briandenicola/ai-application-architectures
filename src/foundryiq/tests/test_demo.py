import copy
import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from scripts import demo


class IngestionTests(unittest.TestCase):
    def test_waits_for_current_upload_not_old_success(self):
        client = unittest.mock.Mock()
        client.request.side_effect = [{"@odata.count": count} for count in (3, 0, 4, 3, 3, 3)]
        with patch.object(demo.time, "sleep") as sleep:
            demo.wait_for_index(
                client,
                {"search_endpoint": "https://search", "search_index": "demo"},
                "current-run",
                3,
            )
        self.assertEqual(sleep.call_count, 2)
        filtered = [
            call.args[3]["filter"]
            for call in client.request.call_args_list
            if "filter" in call.args[3]
        ]
        self.assertEqual(filtered, ["ingestion_run eq 'current-run'"] * 3)

    def test_missing_current_documents_or_empty_index_cannot_report_success(self):
        for expected, counts in [(3, [3, 0]), (3, [2, 2]), (0, [0, 0])]:
            client = unittest.mock.Mock()
            client.request.side_effect = [{"@odata.count": count} for count in counts]
            with (
                self.subTest(expected=expected, counts=counts),
                patch.object(demo.time, "monotonic", side_effect=[0, 1, 301]),
                patch.object(demo.time, "sleep"),
                self.assertRaisesRegex(RuntimeError, "five minutes"),
            ):
                demo.wait_for_index(
                    client,
                    {"search_endpoint": "https://search", "search_index": "demo"},
                    "current-run",
                    expected,
                )


class ResponseTests(unittest.TestCase):
    def response(self):
        return {
            "status": "completed",
            "output": [
                {"type": "mcp_call", "name": "knowledge_base_retrieve", "status": "completed"},
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "20 days [leave-policy.md]."}],
                },
            ],
        }

    def test_answer_requires_successful_retrieval(self):
        self.assertEqual(demo.response_text(self.response()), "20 days [leave-policy.md].")
        for mutation in ("no_tool", "tool_error", "incomplete", "no_answer"):
            response = self.response()
            if mutation == "no_tool":
                response["output"].pop(0)
            elif mutation == "tool_error":
                response["output"][0]["error"] = {"message": "Forbidden"}
            elif mutation == "incomplete":
                response["status"] = "incomplete"
            else:
                response["output"].pop()
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                demo.response_text(response)


class ConfigurationTests(unittest.TestCase):
    def test_teardown_resolves_partial_state_across_regions_but_not_subscriptions(self):
        group = {
            "id": "/subscriptions/original/resourceGroups/synthetic",
            "name": "synthetic",
            "location": "eastus2",
        }
        with patch.object(demo, "state_resource_group", return_value=group):
            with patch.dict(
                demo.os.environ,
                {"AZURE_SUBSCRIPTION_ID": "original", "AZURE_LOCATION": "canadacentral"},
                clear=True,
            ):
                self.assertEqual(demo.resource_group_name(), "synthetic")
            with (
                patch.dict(
                    demo.os.environ,
                    {"AZURE_SUBSCRIPTION_ID": "different", "AZURE_LOCATION": "canadacentral"},
                    clear=True,
                ),
                self.assertRaises(RuntimeError),
            ):
                demo.resource_group_name()

    def test_teardown_without_a_tracked_group_fails_explicitly(self):
        with (
            patch.object(demo, "state_resource_group", return_value=None),
            self.assertRaises(RuntimeError),
        ):
            demo.resource_group_name()

    def test_empty_state_allows_a_new_region_after_destroy(self):
        with (
            patch.dict(demo.os.environ, {"AZURE_LOCATION": "canadacentral"}, clear=True),
            patch.object(demo, "command_json", return_value={"format_version": "1.0"}),
        ):
            demo.verify_state_context()

    def test_preflight_can_retry_partial_state_without_demo_output(self):
        subscription = "00000000-0000-0000-0000-000000000001"
        state = {
            "values": {
                "root_module": {
                    "resources": [
                        {
                            "address": "azurerm_resource_group.this",
                            "values": {
                                "id": f"/subscriptions/{subscription}/resourceGroups/demo",
                                "location": "eastus2",
                            },
                        }
                    ]
                }
            }
        }
        models = [
            {"model": {"name": name, "version": version, "skus": [{"name": sku}]}}
            for name, version, sku in demo.DEFAULT_MODELS.values()
        ]

        def command(args):
            if args[0] == "terraform":
                self.assertEqual(args[2:], ["show", "-json"])
                return state
            if args[1:3] == ["account", "show"]:
                return {"name": "Synthetic subscription", "state": "Enabled"}
            if args[1:3] == ["extension", "show"]:
                return {"name": "containerapp"}
            if args[1:4] == ["search", "usage", "list"]:
                return [{"name": {"value": "basic"}, "currentValue": 1, "limit": 12}]
            self.assertEqual(args[1:4], ["cognitiveservices", "model", "list"])
            return models

        with (
            patch.dict(
                demo.os.environ,
                {
                    "AZURE_SUBSCRIPTION_ID": subscription,
                    "AZURE_LOCATION": "eastus2",
                    "TF_VAR_network_address_space": "10.88.0.0/16",
                },
                clear=True,
            ),
            patch.object(demo.shutil, "which", return_value="/synthetic/tool"),
            patch.object(demo.Path, "exists", return_value=True),
            patch.object(demo, "command_json", side_effect=command) as commands,
        ):
            demo.preflight()
        self.assertTrue(
            any(
                call.args[0][1:4] == ["search", "usage", "list"] for call in commands.call_args_list
            )
        )

    def test_rejects_subscription_and_region_drift(self):
        config = {"subscription_id": "original", "location": "eastus2"}
        for environment in [
            {"AZURE_SUBSCRIPTION_ID": "different", "AZURE_LOCATION": "eastus2"},
            {"AZURE_SUBSCRIPTION_ID": "original", "AZURE_LOCATION": "westus"},
        ]:
            with (
                self.subTest(environment=environment),
                patch.object(demo, "command_json", return_value=config),
                patch.dict(demo.os.environ, environment, clear=True),
                self.assertRaises(RuntimeError),
            ):
                demo.configuration()

    def test_model_check_matches_name_version_and_sku_together(self):
        models = [
            {
                "kind": "OpenAI",
                "skuName": "S0",
                "model": {
                    "name": "gpt-5.4-mini",
                    "version": "2026-03-17",
                    "skus": [{"name": "GlobalStandard"}],
                },
            }
        ]
        demo.verify_model(models, "gpt-5.4-mini", "2026-03-17", "GlobalStandard")
        for name, version, sku in [
            ("other", "2026-03-17", "GlobalStandard"),
            ("gpt-5.4-mini", "other", "GlobalStandard"),
            ("gpt-5.4-mini", "2026-03-17", "Standard"),
        ]:
            with self.subTest(name=name, version=version, sku=sku), self.assertRaises(RuntimeError):
                demo.verify_model(models, name, version, sku)

    def test_model_check_does_not_accept_skus_outside_the_selected_model(self):
        models = [
            {
                "model": {
                    "name": "gpt-5.4-mini",
                    "version": "2026-03-17",
                    "skus": [{"name": "Standard"}],
                },
                "skus": [{"name": "GlobalStandard"}],
            },
            {
                "model": {
                    "name": "gpt-5.5",
                    "version": "2026-04-24",
                    "skus": [{"name": "GlobalStandard"}],
                },
            },
        ]
        with self.assertRaises(RuntimeError):
            demo.verify_model(models, "gpt-5.4-mini", "2026-03-17", "GlobalStandard")


class RestTests(unittest.TestCase):
    def client(self):
        client = demo.AzureRest("subscription")
        client.token = lambda audience: "synthetic-token"
        return client

    def error(self, code):
        return HTTPError(
            "https://example.com", code, "test error", {}, io.BytesIO(b'{"error":"test"}')
        )

    def test_propagation_is_bounded_and_permission_error_surfaces(self):
        with (
            patch.object(demo, "urlopen", side_effect=[self.error(403), self.error(403)]) as send,
            patch.object(demo.time, "monotonic", side_effect=[0, 1, 301]),
            patch.object(demo.time, "sleep") as sleep,
            patch.object(demo.sys, "stdout", new_callable=io.StringIO) as output,
            self.assertRaises(demo.ServiceError) as raised,
        ):
            self.client().request("PUT", "https://example.com", "audience", propagation=True)
        self.assertEqual(raised.exception.status, 403)
        self.assertEqual(send.call_count, 2)
        sleep.assert_called_once_with(10)
        self.assertIn("PUT https://example.com", output.getvalue())
        self.assertIn('{"error":"test"}', output.getvalue())

    def test_post_server_error_is_not_replayed(self):
        with (
            patch.object(demo, "urlopen", side_effect=self.error(500)) as send,
            patch.object(demo.time, "sleep") as sleep,
            self.assertRaises(demo.ServiceError),
        ):
            self.client().request("POST", "https://example.com", "audience", {})
        send.assert_called_once()
        sleep.assert_not_called()


class SetupTests(unittest.TestCase):
    def config(self):
        return {
            "subscription_id": "subscription",
            "storage_account": "storage",
            "storage_resource_id": "/subscriptions/subscription/storage",
            "container_name": "handbook",
            "search_endpoint": "https://search.example.com",
            "search_index": "handbook-index",
            "knowledge_source": "handbook-source",
            "knowledge_base": "handbook",
            "openai_endpoint": "https://model.example.com",
            "chat_deployment": "chat",
            "chat_model": "gpt-5.4-mini",
            "embedding_deployment": "embedding",
            "embedding_model": "text-embedding-3-small",
            "project_resource_id": "/subscriptions/subscription/project",
            "project_endpoint": "https://project.example.com",
            "connection_name": "handbook-mcp",
            "agent_name": "handbook-agent",
            "application_insights_id": "/subscriptions/subscription/components/insights",
            "application_insights_app_id": "synthetic-application",
            "telemetry_connection_name": "handbook-insights",
        }

    def run_setup(self, exists):
        calls = []

        def request(method, url, audience, payload=None, **kwargs):
            calls.append((method, url, audience, copy.deepcopy(payload)))
            if method == "GET" and "/agents/" in url and not exists:
                raise demo.ServiceError(404, method, url, "Not found")
            return {}

        client = unittest.mock.Mock()
        client.request.side_effect = request

        def index_after_uploads(client, config):
            uploads = [
                call for call in calls if call[0] == "PUT" and ".blob.core.windows.net/" in call[1]
            ]
            self.assertEqual(len(uploads), len(list((demo.ROOT / "data").glob("*.md"))))

        with patch.object(demo, "index_blobs", side_effect=index_after_uploads) as index:
            demo.setup(client, self.config())
        index.assert_called_once_with(client, self.config())
        return calls

    def test_setup_wires_existing_index_and_shared_knowledge_base(self):
        calls = self.run_setup(exists=False)
        payloads = [payload for _, _, _, payload in calls if isinstance(payload, dict)]
        source = next(payload for payload in payloads if payload.get("name") == "handbook-source")
        self.assertEqual(source["kind"], "searchIndex")
        self.assertEqual(source["searchIndexParameters"]["searchIndexName"], "handbook-index")
        connection = next(
            payload
            for payload in payloads
            if payload.get("properties", {}).get("category") == "RemoteTool"
        )
        self.assertEqual(connection["properties"]["authType"], "ProjectManagedIdentity")
        agent = next(payload for payload in payloads if "definition" in payload)
        tool = agent["definition"]["tools"][0]
        self.assertEqual(tool["server_url"], connection["properties"]["target"])
        self.assertEqual(tool["allowed_tools"], ["knowledge_base_retrieve"])
        self.assertNotIn("apiKey", json.dumps(payloads))
        self.assertFalse(any("handbook-insights" in url for _, url, _, _ in calls))
        self.assertTrue(any(url.endswith("/agents?api-version=v1") for _, url, _, _ in calls))

    def test_repeat_setup_creates_version_instead_of_duplicate_agent(self):
        calls = self.run_setup(exists=True)
        self.assertTrue(
            any(url.endswith("/handbook-agent/versions?api-version=v1") for _, url, _, _ in calls)
        )
        self.assertFalse(any(url.endswith("/agents?api-version=v1") for _, url, _, _ in calls))


if __name__ == "__main__":
    unittest.main()
