# Offline guard tamper log

## 2026-11-24

Disabled each guard below independently in an in-memory copy of its Python
function, ran the corresponding existing unit test, and confirmed an assertion
failure rather than a test error. Restored the original function after each
mutation. No policy files, Azure services, or on-disk implementation were changed
by the mutations.

| Disabled guard | Test detecting the mutation |
|---|---|
| Reject an ingestion result from before the latest upload | `IngestionTests.test_waits_for_current_upload_not_old_success` |
| Reject ingestion errors or a nonzero failure count | `IngestionTests.test_failed_or_partial_ingestion_is_not_success` |
| Reject failed or partially successful synchronization | `IngestionTests.test_failed_or_partial_ingestion_is_not_success` |
| Reject a successful run processing zero documents | `IngestionTests.test_failed_or_partial_ingestion_is_not_success` |
| Reject an incomplete or errored Foundry response | `ResponseTests.test_answer_requires_successful_retrieval` |
| Reject an answer without an MCP call | `ResponseTests.test_answer_requires_successful_retrieval` |
| Reject a failed MCP call | `ResponseTests.test_answer_requires_successful_retrieval` |
| Reject a response without an assistant answer | `ResponseTests.test_answer_requires_successful_retrieval` |
| Reject subscription drift from Terraform state | `ConfigurationTests.test_rejects_subscription_and_region_drift` |
| Reject region drift from Terraform state | `ConfigurationTests.test_rejects_subscription_and_region_drift` |
| Reject an unavailable model/version/SKU combination | `ConfigurationTests.test_model_check_matches_name_version_and_sku_together` |

Result: all 11 mutations detected. After restoring the originals, `task check`
passed all nine unit tests, Ruff lint/format checks, and Terraform formatting.
This proves only the tested local failure handling, not live service behavior.
