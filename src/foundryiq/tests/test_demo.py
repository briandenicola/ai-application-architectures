import copy
import io
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from urllib.error import HTTPError

from scripts import demo

SINCE = datetime(2026, 1, 1, tzinfo=timezone.utc)


class IngestionTests(unittest.TestCase):
    def state(self, **changes):
        state = {
            "status": "success",
            "startTime": "2026-01-01T00:01:00Z",
            "itemUpdatesProcessed": 3,
            "itemsUpdatesFailed": 0,
        }
        state.update(changes)
        return {"lastSynchronizationState": state}

    def test_waits_for_current_upload_not_old_success(self):
        self.assertFalse(demo.ingestion_complete({}, SINCE))
        self.assertFalse(
            demo.ingestion_complete(self.state(startTime="2025-12-31T23:59:00Z"), SINCE)
        )
        self.assertFalse(demo.ingestion_complete(self.state(status="inProgress"), SINCE))
        self.assertTrue(demo.ingestion_complete(self.state(), SINCE))

    def test_failed_or_partial_ingestion_is_not_success(self):
        for state in [
            self.state(status="partialSuccess"),
            self.state(status="failure"),
            self.state(itemsUpdatesFailed=1),
            self.state(errors=[{"errorMessage": "Permission denied"}]),
            self.state(itemUpdatesProcessed=0),
        ]:
            with self.subTest(state=state), self.assertRaises(RuntimeError):
                demo.ingestion_complete(state, SINCE)


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
            self.assertRaises(demo.ServiceError) as raised,
        ):
            self.client().request("PUT", "https://example.com", "audience", propagation=True)
        self.assertEqual(raised.exception.status, 403)
        self.assertEqual(send.call_count, 2)
        sleep.assert_called_once_with(10)

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
        }

    def run_setup(self, exists):
        calls = []

        def request(method, url, audience, payload=None, **kwargs):
            calls.append((method, url, audience, copy.deepcopy(payload)))
            if method == "GET" and not exists:
                raise demo.ServiceError(404, method, url, "Not found")
            return {}

        client = unittest.mock.Mock()
        client.request.side_effect = request
        with patch.object(demo, "wait_for_ingestion"):
            demo.setup(client, self.config())
        return calls

    def test_setup_wires_blob_identity_and_shared_knowledge_base(self):
        calls = self.run_setup(exists=False)
        payloads = [payload for _, _, _, payload in calls if isinstance(payload, dict)]
        source = next(payload for payload in payloads if payload.get("kind") == "azureBlob")
        self.assertEqual(
            source["azureBlobParameters"]["connectionString"],
            "ResourceId=/subscriptions/subscription/storage",
        )
        connection = next(payload for payload in payloads if "properties" in payload)
        self.assertEqual(connection["properties"]["authType"], "ProjectManagedIdentity")
        agent = next(payload for payload in payloads if "definition" in payload)
        tool = agent["definition"]["tools"][0]
        self.assertEqual(tool["server_url"], connection["properties"]["target"])
        self.assertEqual(tool["allowed_tools"], ["knowledge_base_retrieve"])
        self.assertNotIn("apiKey", json.dumps(payloads))
        self.assertTrue(any(url.endswith("/agents?api-version=v1") for _, url, _, _ in calls))

    def test_repeat_setup_creates_version_instead_of_duplicate_agent(self):
        calls = self.run_setup(exists=True)
        self.assertTrue(
            any(url.endswith("/handbook-agent/versions?api-version=v1") for _, url, _, _ in calls)
        )
        self.assertFalse(any(url.endswith("/agents?api-version=v1") for _, url, _, _ in calls))


if __name__ == "__main__":
    unittest.main()
