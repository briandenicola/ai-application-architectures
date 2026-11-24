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

## 2026-11-24: model-catalog regression

The initial catalog test incorrectly placed `skus` beside `model`, matching a bug
in the preflight rather than Azure CLI's actual catalog response.

Updated the fixture to use `model.skus` and added a negative case rejecting a SKU
from the wrong level or a different model. Before fixing production code, the
positive case raised the reported availability error and the negative case
failed its assertion. Corrected the lookup to use only the selected model's
`skus`.

The user approved replacing the chat default with `gpt-5.4-mini`, version
`2026-03-17`, and updating the ignored local `.env`. The model/version/SKU and
available quota were confirmed by read-only `eastus2` catalog and usage queries.

After the fix, all ten tests passed, Terraform schema validation passed, and the
actual preflight succeeded against the selected subscription and `eastus2`.
No Azure provisioning was performed.
