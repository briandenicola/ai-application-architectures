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

## 2026-11-24: failed-deployment recovery and serialization

The reported deployment exposed two additional problems: Foundry child resources
were written concurrently, and preflight expected the final `demo` output even
when a failed apply had not produced it.

Before the fix, the new dependency-graph test failed for both project-to-chat and
chat-to-embedding ordering. The partial-state test failed because preflight
requested the missing output instead of reading the existing resource group's
subscription and region from state.

The fix uses explicit project -> chat -> embedding dependencies and retains
address moves for existing model state. Preflight now validates context from
partial state, while an empty state after destruction permits a new region.
`task down` uses Terraform's interactive destroy and retains local state files.

Canada Central's catalog advertises both selected models on GlobalStandard; the
regional Standard embedding SKU is not advertised there. Read-only usage queries
confirmed quota for both GlobalStandard deployments. Physical Search capacity
was not tested by creating a service.

After the fixes, `task check` passed Terraform schema validation, Ruff, and all
thirteen tests, including the native dependency-graph assertions.
`task --dry down` confirmed initialization followed by interactive destruction;
no destroy command was executed.

## 2026-11-24: fast resource-group teardown

Replaced interactive `terraform destroy` with the document-intelligence
Taskfile's `az group delete --yes --no-wait` pattern and local artifact cleanup.
The resource group resolver reads partial state and permits a region change for
teardown, but still rejects a subscription mismatch. Added focused tests for
those cases and for missing group state.

The Taskfile blocks cleanup while a Terraform lock exists. Azure deletion
failure stops the task before state removal; the provider version lock remains
tracked.

Ran the actual `task down` target inside temporary fixtures using a fake Azure
CLI: verified the asynchronous deletion arguments, state/cache removal after
acceptance, state preservation after rejection, and no deletion while locked.
Disabled each of the subscription, missing-group, deletion-failure, and state-lock
guards independently in memory or the temporary Taskfile copy. Each mutation
caused an assertion failure; all four tests passed again after restoration.
Production code and real deployment state were not mutated by these checks.

Ruff lint/format checks and all sixteen Python/teardown tests passed. The full
`task check` stopped at Terraform validation because the local provider cache is
absent; the unchanged infrastructure dependency-graph test was not rerun.
No live Azure deletion or provisioning was executed.

## 2026-11-24: private Blob access and setup identity (initial S2 design)

This records commit `1e4596a`. The Basic correction below replaces its managed
Blob ingestion and shared-link guards; those historical tests are no longer active.

Read-only inspection reproduced the Blob network denial and confirmed that the
live account had public access disabled by policy. The Azure CLI token's object
ID also differed from Terraform's Blob-contributor principal. Waiting for role
propagation could not fix either condition.

The user approved private Blob access, S2, a new private setup runner, Terraform
generation, and the VNet CIDR. Implemented private upload endpoint/DNS, a separate
Search ingestion shared private link, and a manual managed-identity job.
Deployment credentials no longer select the operator's data-plane permissions.

Disabled or inverted the following independently in memory, except for the two
Terraform dependency mutations, which used isolated copies and the existing
provider cache. Production code, real deployment state, and Azure resources were
not mutated.

| Disabled guard | Detecting test |
|---|---|
| Reject Basic for private managed ingestion | `test_private_ingestion_rejects_basic_and_invalid_network_ranges` |
| Require space for two runner/endpoint subnets | `test_private_ingestion_rejects_basic_and_invalid_network_ranges` |
| Resolve Blob exclusively to the configured private endpoint | `test_worker_requires_exclusively_the_configured_private_endpoint` |
| Fail Blob network denial without blind RBAC retries | `test_blob_network_denial_fails_without_propagation_retries` |
| Approve only this demo's matching connection | `test_only_approves_the_matching_connection_and_waits_for_readiness` |
| Wait for successful provisioning after approval | `test_approved_link_still_waits_for_successful_provisioning` |
| Reject rejected/disconnected links | `test_rejected_link_and_ambiguous_connections_fail_explicitly` |
| Reject failed link provisioning | `test_rejected_link_and_ambiguous_connections_fail_explicitly` |
| Reject ambiguous approval targets | `test_rejected_link_and_ambiguous_connections_fail_explicitly` |
| Do not reapprove a rejected target connection | `test_rejected_target_connection_is_not_reapproved` |
| Bound waiting for an unmatched approval request | `test_unmatched_request_times_out_without_approving_other_connections` |
| Require the provisioned private runner | `test_legacy_state_requires_provisioning_before_setup` |
| Reject known-active setup executions | `test_existing_execution_prevents_another_start` |
| Check subsequent execution-list pages | `test_existing_execution_prevents_another_start` |
| Fail failed/stopped executions instead of reporting success | `test_job_status_controls_success_and_failure` |
| Fail a timed-out execution | `test_running_job_times_out_instead_of_reporting_success` |
| Exclude local credentials and state from the worker bundle | `test_bundle_excludes_local_credentials_and_terraform_state` |
| Reject a bundle without policy documents | `test_empty_policy_bundle_cannot_start_a_demo` |
| Preserve the worker's failure exit code | `test_bootstrap_logs_in_with_managed_identity_and_preserves_worker_exit_code` |
| Dispatch local setup to the private job | `test_local_setup_dispatches_to_job_not_local_blob_uploads` |
| Actually invoke private DNS validation inside the worker | `test_worker_uses_supplied_configuration_without_terraform` |
| Configure the knowledge source for private ingestion | `test_setup_wires_blob_identity_and_shared_knowledge_base` |
| Derive the operator from the Azure CLI identity claim | `test_operator_uses_cli_token_identity_not_terraform_credentials` |
| Make the job wait for the private DNS VNet link | `test_foundry_and_private_setup_dependency_ordering` |
| Make the job wait for its NAT subnet association | `test_foundry_and_private_setup_dependency_ordering` |

All 25 mutations produced assertion failures, not test errors. After restoring
the originals, all 35 tests passed. `task check` also passed Terraform schema and
format validation plus Ruff lint/format checks. `task --dry up` confirmed the
user-run command sequence without provisioning or invoking setup.

These are offline contract and failure-handling checks, not a successful live
private deployment. The user must run `task up` to apply the new infrastructure
and exercise the private worker, ingestion, Foundry agent, and Copilot Studio.

## 2026-11-24: Basic Search with private runner indexing

The S2 update failed because the subscription had zero regional S2 quota.
Read-only checks confirmed Basic was still healthy, with available Basic quota.
The user explicitly selected runner-based Blob indexing on Basic, rather than a
quota request or another region.

Mutated the following independently in memory. The final Terraform mutation
used an isolated source copy and the existing provider cache. No real state,
Azure resources, credentials, or production source files were changed by tampering.

| Disabled or altered behavior | Detecting test |
|---|---|
| Reject zero/exhausted service quota | `QuotaTests` |
| Reject missing tier quota | `QuotaTests` |
| Fail rather than succeed after quota exhaustion | `QuotaTests` |
| Limit full-quota retries to the existing tier | `QuotaTests` |
| Actually invoke quota checking from preflight | `test_preflight_can_retry_partial_state_without_demo_output` |
| Reject unsupported Free tier | `test_private_runner_accepts_basic_but_rejects_free_and_invalid_network_ranges` |
| Follow Blob continuation pages | `test_blob_downloads_follow_pages_and_skip_non_markdown` |
| Select Markdown policy blobs only | `test_blob_downloads_follow_pages_and_skip_non_markdown` |
| Reject an empty individual policy | `test_empty_blob_or_missing_markdown_fails_before_indexing` |
| Reject a container without Markdown content | `test_empty_blob_or_missing_markdown_fails_before_indexing` |
| Bound embedding chunks | `test_indexes_blob_chunks_with_vectors_and_reconciles_old_chunks` |
| Preserve raw Blob response bytes | `test_raw_blob_response_is_not_parsed_as_json` |
| Validate every index-action result | `test_partial_or_mismatched_index_results_fail_for_upload_and_delete` |
| Require the current run's documents | `IngestionTests` |
| Require obsolete chunks to be gone | `IngestionTests` |
| Never accept an empty visible index | `IngestionTests` |
| Fail when current-run visibility times out | `IngestionTests` |
| Follow existing-index document pages | `test_indexes_blob_chunks_with_vectors_and_reconciles_old_chunks` |
| Reconcile obsolete chunks | `test_indexes_blob_chunks_with_vectors_and_reconciles_old_chunks` |
| Actually invoke indexing during setup | `SetupTests` |
| Complete uploads before reading Blob for indexing | `SetupTests` |
| Use an existing-index knowledge source | `test_setup_wires_existing_index_and_shared_knowledge_base` |
| Reject incomplete embedding batches | Isolated assertion using the indexing test's mocked fixture |
| Reject incompatible embedding dimensions | Isolated assertion using the indexing test's mocked fixture |
| Wait for the runner's embedding-model role | `test_foundry_and_private_setup_dependency_ordering` |

All 25 mutations caused assertion failures, with no test errors. After restoring
the originals, all 39 tests passed. Final `task check` also passed Terraform
format/schema validation and Ruff lint/format checks. `git diff --check` passed.
These checks do not prove live indexing or either agent's Azure integration.

## Foundry observability guards

After adding keyless monitoring and response-correlated diagnostics, independently
broke these guards in memory or isolated Terraform copies. Each mutation produced
an assertion failure, with zero test errors. Runtime originals were restored in
`finally`; the real Terraform files, state, and Azure resources were not mutated.

| Broken guard | Detecting test |
|---|---|
| Accept unsafe response IDs | `test_query_is_exact_response_scoped_then_expands_only_its_operations` |
| Remove the exact response-ID seed | Same correlation test |
| Return unrelated operations | Same correlation test |
| Expand the query's lookback | Same correlation test |
| Accept partial query errors | `test_partial_missing_or_malformed_query_data_is_not_success` |
| Accept missing result tables | Same query-schema test |
| Accept a missing PrimaryResult | Same query-schema test |
| Accept malformed rows | Same query-schema test |
| Remove configuration checks before a paid request | `test_legacy_config_and_invalid_wait_fail_before_agent_call` |
| Accept only one required telemetry identifier | Same pre-request test |
| Accept a negative wait | Same pre-request test |
| Report absent telemetry as observed | `test_timeout_remains_pending_and_retry_preserves_original_response` |
| Make another query after the polling deadline | `test_positive_wait_stops_at_deadline_without_an_extra_query` |
| Swallow query/auth failures | `test_query_failure_is_recorded_and_propagated_not_treated_as_pending` |
| Swallow an agent/tool failure | `test_ask_prints_details_and_collects_traces_even_on_validation_failure` |
| Mask the agent failure with a telemetry failure | `test_agent_failure_is_not_masked_by_a_second_telemetry_failure` |
| Replace the connection's project identity with key auth | `test_setup_wires_existing_index_and_shared_knowledge_base` |
| Point the telemetry connection at the wrong resource | Same connection wiring test |
| Omit the helper from the worker bundle | `test_real_worker_bundle_imports_without_runtime_packages` |
| Accept a script-only bundle without policies | `test_empty_policy_bundle_cannot_start_a_demo` |
| Start setup without the publisher-role dependency | `test_foundry_and_private_setup_dependency_ordering` |
| Disconnect App Insights from its workspace | Same native Terraform graph test |
| Publish under an identity other than the project | Same native Terraform graph test |

All **23 mutations** were detected. After restoring originals, the offline gate
covers 50 tests plus Terraform format/schema and Ruff lint/format. Native graph
checks use installed providers and no Azure operations. The existing Basic
setup was confirmed working by the user; this proof does not verify the new
live telemetry connection, ingestion, or query results.
