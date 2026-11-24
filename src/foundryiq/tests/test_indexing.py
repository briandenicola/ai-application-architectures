import unittest
import uuid
from unittest.mock import Mock, patch

from scripts import demo


class IndexingTests(unittest.TestCase):
    def config(self):
        return {
            "storage_account": "synthetic",
            "container_name": "handbook",
            "search_endpoint": "https://search.example.com",
            "search_index": "handbook-index",
            "openai_endpoint": "https://model.example.com",
            "embedding_deployment": "embedding",
            "embedding_model": "text-embedding-3-small",
        }

    def test_blob_downloads_follow_pages_and_skip_non_markdown(self):
        client = Mock()

        def request(method, url, audience, **kwargs):
            if "marker=a%2B%2F%3D" in url:
                return (
                    b"<EnumerationResults><Blobs><Blob><Name>folder/second policy.md</Name>"
                    b"</Blob></Blobs><NextMarker/></EnumerationResults>"
                )
            if "comp=list" in url:
                return (
                    b"<EnumerationResults><Blobs><Blob><Name>first.md</Name></Blob>"
                    b"<Blob><Name>ignored.txt</Name></Blob></Blobs><NextMarker>a+/=</NextMarker>"
                    b"</EnumerationResults>"
                )
            return {
                "first.md": b"# First\n\nPolicy from Blob, not local files.",
                "second%20policy.md": b"# Second\n\nAnother Blob policy.",
                "ignored.txt": b"Not a Markdown policy.",
            }[url.rsplit("/", 1)[1]]

        client.request.side_effect = request
        documents = demo.blob_chunks(client, self.config(), "run")
        self.assertEqual(len(documents), 2)
        self.assertIn("from Blob", documents[0]["content"])
        self.assertTrue(documents[1]["url"].endswith("/folder/second%20policy.md"))
        self.assertIn("marker=a%2B%2F%3D", client.request.call_args_list[2].args[1])
        self.assertTrue(all(call.kwargs["raw"] for call in client.request.call_args_list))

    def test_empty_blob_or_missing_markdown_fails_before_indexing(self):
        for responses in [
            [b"<EnumerationResults><Blobs/></EnumerationResults>"],
            [
                b"<EnumerationResults><Blobs><Blob><Name>empty.md</Name></Blob>"
                b"<Blob><Name>valid.md</Name></Blob></Blobs>"
                b"</EnumerationResults>",
                b" \n",
                b"# Valid policy",
            ],
        ]:
            client = Mock()
            client.request.side_effect = responses
            with self.subTest(responses=responses), self.assertRaises(RuntimeError):
                demo.blob_chunks(client, self.config(), "run")
            self.assertTrue(all(call.args[0] == "GET" for call in client.request.call_args_list))

    def test_indexes_blob_chunks_with_vectors_and_reconciles_old_chunks(self):
        config = self.config()
        uploaded = []
        deleted = []
        current_id = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL, "https://synthetic.blob.core.windows.net/handbook/cloud.md#0"
            )
        )

        def request(method, url, audience, payload=None, **kwargs):
            if ".blob.core.windows.net" in url:
                self.assertEqual(audience, demo.STORAGE_AUDIENCE)
                self.assertTrue(kwargs["raw"])
                if "comp=list" in url:
                    return (
                        b"<EnumerationResults><Blobs><Blob><Name>cloud.md</Name></Blob>"
                        b"</Blobs></EnumerationResults>"
                    )
                return ("# Cloud policy\n\n" + "a" * 2500).encode()
            if method == "PUT":
                self.assertEqual(payload["name"], config["search_index"])
                vectorizer = payload["vectorSearch"]["vectorizers"][0]
                self.assertEqual(vectorizer["azureOpenAIParameters"]["deploymentId"], "embedding")
                self.assertNotIn("apiKey", vectorizer["azureOpenAIParameters"])
                return {}
            if url.endswith("/embeddings"):
                self.assertEqual(audience, demo.OPENAI_AUDIENCE)
                return {
                    "data": [
                        {"index": i, "embedding": [float(i)] * demo.EMBEDDING_DIMENSIONS}
                        for i in reversed(range(len(payload["input"])))
                    ]
                }
            if "/docs/index?" in url:
                for action in payload["value"]:
                    (uploaded if action["@search.action"] == "upload" else deleted).append(action)
                return {"value": [{"key": item["id"], "status": True} for item in payload["value"]]}
            if "select" in payload:
                if payload["skip"] == 0:
                    return {
                        "value": [
                            {"id": current_id},
                            *[{"id": f"stale-{i:04d}"} for i in range(999)],
                        ]
                    }
                self.assertEqual(payload["skip"], 1000)
                return {"value": [{"id": "stale-last"}]}
            if "filter" in payload:
                self.assertEqual(
                    payload["filter"], f"ingestion_run eq '{uploaded[0]['ingestion_run']}'"
                )
            return {"@odata.count": len(uploaded)}

        client = Mock()
        client.request.side_effect = request
        demo.index_blobs(client, config)
        self.assertEqual(len(uploaded), 3)
        self.assertEqual(len({item["id"] for item in uploaded}), 3)
        self.assertTrue(all(0 < len(item["content"]) <= 2000 for item in uploaded))
        self.assertTrue(all("cloud.md" in item["title"] for item in uploaded))
        self.assertTrue(all("content_vector" in item for item in uploaded))
        self.assertEqual([item["content_vector"][0] for item in uploaded], [0.0, 1.0, 2.0])
        self.assertEqual(
            {item["id"] for item in deleted},
            {*[f"stale-{i:04d}" for i in range(999)], "stale-last"},
        )
        self.assertTrue(all(item["@search.action"] == "delete" for item in deleted))

    def test_partial_or_mismatched_index_results_fail_for_upload_and_delete(self):
        for action in ("upload", "delete"):
            for results in (
                [],
                [{"key": "policy", "status": False, "errorMessage": "Denied"}],
                [{"key": "other", "status": True}],
                [{"key": "policy", "status": True}] * 2,
            ):
                client = Mock()
                client.request.return_value = {"value": results}
                with (
                    self.subTest(action=action, results=results),
                    self.assertRaisesRegex(RuntimeError, "batch failed or was incomplete"),
                ):
                    demo.write_index_batch(
                        client, self.config(), [{"@search.action": action, "id": "policy"}]
                    )

    def test_incomplete_or_wrong_dimension_embeddings_never_upload_documents(self):
        for data in (
            [],
            [{"index": 0, "embedding": [0.1]}],
            [{"index": 1, "embedding": [0.1] * demo.EMBEDDING_DIMENSIONS}],
        ):
            client = Mock()
            client.request.side_effect = [{}, {"value": []}, {"data": data}]
            with (
                self.subTest(data=data),
                patch.object(
                    demo, "blob_chunks", return_value=[{"id": "policy", "content": "Policy"}]
                ),
                self.assertRaisesRegex(RuntimeError, "Embedding response"),
                patch.object(demo, "write_index_batch") as write,
                patch.object(demo, "wait_for_index"),
            ):
                demo.index_blobs(client, self.config())
            write.assert_not_called()
            self.assertFalse(
                any("/docs/index?" in call.args[1] for call in client.request.call_args_list)
            )

    def test_failed_upload_does_not_delete_existing_chunks(self):
        client = Mock()
        client.request.side_effect = [
            {},
            {"value": [{"id": "stale"}]},
            {"data": [{"index": 0, "embedding": [0.1] * demo.EMBEDDING_DIMENSIONS}]},
            {"value": [{"key": "policy", "status": False, "errorMessage": "Denied"}]},
        ]
        with (
            patch.object(demo, "blob_chunks", return_value=[{"id": "policy", "content": "Policy"}]),
            self.assertRaisesRegex(RuntimeError, "batch failed"),
        ):
            demo.index_blobs(client, self.config())
        actions = [
            item
            for call in client.request.call_args_list
            if "/docs/index?" in call.args[1]
            for item in call.args[3]["value"]
        ]
        self.assertEqual([item["@search.action"] for item in actions], ["upload"])

    def test_raw_blob_response_is_not_parsed_as_json(self):
        client = demo.AzureRest("subscription")
        client.token = Mock(return_value="synthetic-token")
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = b"# Policy\n\nBlob content."
        with patch.object(demo, "urlopen", return_value=response):
            self.assertEqual(
                client.request(
                    "GET",
                    "https://synthetic.blob.core.windows.net/handbook/policy.md",
                    demo.STORAGE_AUDIENCE,
                    raw=True,
                ),
                response.read.return_value,
            )


class QuotaTests(unittest.TestCase):
    def test_zero_exhausted_or_missing_quota_blocks_provisioning(self):
        for usages, message in [
            ([{"name": {"value": "basic"}, "currentValue": 0, "limit": 0}], "limit 0"),
            ([{"name": {"value": "basic"}, "currentValue": 12, "limit": 12}], "limit 12"),
            ([], "did not include"),
        ]:
            with (
                self.subTest(usages=usages),
                patch.dict(demo.os.environ, {"TF_VAR_search_sku": "basic"}, clear=True),
                patch.object(demo.Path, "exists", return_value=False),
                patch.object(demo, "command_json", return_value=usages),
                self.assertRaisesRegex(RuntimeError, message),
            ):
                demo.verify_search_quota("subscription", "canadacentral")

    def test_available_quota_or_existing_same_tier_allows_retry_but_not_tier_change(self):
        for current, tracked_sku, allowed in [
            (0, None, True),
            (1, "basic", True),
            (1, "standard", False),
        ]:
            usages = [{"name": {"value": "basic"}, "currentValue": current, "limit": 1}]
            state = {
                "values": {
                    "root_module": {
                        "resources": [
                            {
                                "address": "azurerm_search_service.this",
                                "values": {"sku": tracked_sku, "location": "canadacentral"},
                            }
                        ]
                    }
                }
            }
            with (
                self.subTest(current=current, tracked_sku=tracked_sku),
                patch.dict(demo.os.environ, {"TF_VAR_search_sku": "basic"}, clear=True),
                patch.object(demo.Path, "exists", return_value=True),
                patch.object(
                    demo,
                    "command_json",
                    side_effect=lambda args, state=state, usages=usages: (
                        state if args[0] == "terraform" else usages
                    ),
                ),
            ):
                if allowed:
                    demo.verify_search_quota("subscription", "canadacentral")
                else:
                    with self.assertRaisesRegex(RuntimeError, "Request quota"):
                        demo.verify_search_quota("subscription", "canadacentral")
