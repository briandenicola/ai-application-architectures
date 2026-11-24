# Foundry IQ demo deployment plan

Status: Ready for Validation

## Confirmed scope

- Self-contained demo in `src/foundryiq`.
- All changes must remain inside `src/foundryiq`; do not modify other directories.
- Terraform infrastructure and a small set of Taskfile targets.
- New Azure resources; the user runs all provisioning and execution tasks.
- Synthetic employee handbook covering leave, expenses, and remote work.
- One Blob-backed Foundry IQ knowledge base shared by a Foundry agent and a
  Copilot Studio agent.
- Keyless authentication and a Copilot Studio connection walkthrough.

## Architecture and recipe

- Recipe: Terraform driven by Taskfile, matching the repository standard;
  no azd wrapper, web application, or hosted-agent runtime. A manual Container
  Apps job performs setup inside a private VNet.
- One resource group, one StorageV2 account with a private blob container,
  one Azure AI Search service, one Foundry account, and one Foundry project.
- The private runner reads Blob policies, chunks/embeds them, and pushes a Basic
  Search index. A search-index knowledge source and shared knowledge base expose
  retrieval to both agents. Search uses the same embedding model for query vectors.
- A Foundry prompt agent calls the knowledge base through its MCP endpoint and
  a project-managed-identity connection.
- Copilot Studio uses its native Foundry IQ tool, the Search service endpoint,
  and Microsoft Entra ID Integrated authentication.
- A small chat model serves the Foundry agent and knowledge-base query planning;
  an embedding model handles indexing. Model names, versions, deployment SKUs,
  capacities, subscription, and region are environment configuration.
- Resource names derive from `random_pet` and `random_id`.
- Terraform creates infrastructure and RBAC. Python automation uploads synthetic
  documents, creates the knowledge source/base, waits for ingestion, and creates
  the Foundry prompt agent from the VNet-integrated managed-identity job.
- Principal Task targets: `up`, `down`, `setup`, `ask`, `traces`, `outputs`, and `check`. `up` includes
  provisioning and setup; `ask` exercises the deployed Foundry agent.

## Execution boundary

Prepare and validate repository files only. The user executes provisioning,
setup, and deletion. Scoped read-only Azure troubleshooting is permitted;
those observations do not prove future capacity or successful provisioning.
Do not install dependencies, run local containers, or perform Azure writes
without approval.

## Approved configuration

- Target region: `canadacentral`, configurable in `.env`.
- Blob public access disabled; private endpoint/DNS for runner uploads/downloads.
  No Search shared private link or managed Blob ingestion is used.
- Search Basic and runner-driven indexing explicitly approved after the S2
  quota failure. The private setup runner is retained. Search and
  Foundry retain Entra-authenticated public endpoints for native Copilot Studio.
- VNet CIDR `10.88.0.0/16` explicitly approved and supplied via ignored `.env`.
  Two distinct `/27` subnets are derived, not hardcoded as deployment addresses.
- User-selected region and subscription supplied in an ignored `.env`.
- Local, offline validation approved; all Azure execution remains with the user.
- Use a prompt agent and standard-library Python REST automation. The runner
  uses a pinned official Azure CLI image with managed identity; no custom image
  build, application packages, SSH, API keys, or credentials.

## References

- https://learn.microsoft.com/azure/search/agentic-knowledge-source-how-to-search-index
- https://learn.microsoft.com/azure/search/agentic-retrieval-how-to-create-index
- https://learn.microsoft.com/azure/foundry/agents/how-to/foundry-iq-connect
- https://learn.microsoft.com/microsoft-copilot-studio/agents-experience/foundry-iq-connect

## Implementation

- [x] Inspect repository conventions and official service documentation.
- [x] Present the complete plan and obtain approval.
- [x] Generate Terraform, Taskfile, sample data, scripts, and walkthrough.
- [x] Prepare validation commands for the user.

## Preparation results

- Initial offline formatting, lint, and nine mocked-service unit tests passed.
- Eleven in-memory guard mutations were detected by the existing tests;
  originals were restored and `task check` passed again. See `docs/tamper-log.md`.
- The user subsequently approved Terraform provider downloads for local schema
  validation. Initialization and `terraform validate` passed; no Azure
  operations were authorized or executed.
- `task up` runs provider initialization and Terraform validation before apply.
- Azure provisioning, regional quota/capacity, live ingestion, agent execution,
  and Copilot Studio integration remain unverified until the user runs the demo.

## Validation proof

- Passed: `task check` (Terraform format, Ruff lint/format, nine unit tests).
- Passed: `task --list` and dry-run question forwarding through `task ask`.
- Passed after explicit download approval:
  `terraform -chdir=infra init -backend=false -input=false -no-color` and
  `terraform -chdir=infra validate -no-color`.
- Deferred to user: Azure authentication, Terraform plan review, live
  provisioning, quota/capacity checks, live ingestion/retrieval, and Copilot
  Studio preview.

## Model-catalog correction

- Read-only troubleshooting confirmed Azure CLI nests deployment SKUs under
  `model.skus`, not at the catalog entry's root.
- The user approved fixing the parser and changing the chat model to
  `gpt-5.4-mini`, version `2026-03-17`, with `GlobalStandard` deployment.
- Updated the Python/Terraform/example defaults and ignored local `.env`.
- Catalog presence and available quota were confirmed in `eastus2` using
  read-only Azure queries; no resources were provisioned or changed.
- Passed after the correction: `task check` (ten tests),
  `terraform -chdir=infra validate -no-color`, and the actual read-only preflight
  using the updated `.env`.
- Terraform plan/apply and end-to-end ingestion, agent, and Copilot Studio
  verification remain for the user to run.

## Deployment recovery and Canada move

- The user requested the entire demo move to Canada Central, plus `task down`
  and naming matching the existing repository. The user runs destruction and
  provisioning; no Azure writes are authorized for the assistant.
- Added interactive `task down`; it does not delete state files or suppress
  failures. Run it against the current partial deployment before `task up`.
- Updated defaults and the ignored `.env` to `canadacentral` and embedding
  `GlobalStandard`. Read-only catalog and usage queries confirmed both selected
  model/version/SKU combinations and available quota in Canada Central.
- Matched `infrastructure/microsoft-foundry/main.tf` and `rg.tf` naming:
  pet + decimal random ID, followed by service suffixes. Search and Storage
  naming follow `infrastructure/agent-service/project/main.tf`.
- Serialized Foundry project/chat/embedding writes to remove concurrent
  operations against the parent account. Model address moves preserve Terraform
  tracking of the existing embedding deployment during cleanup.
- Fixed preflight to validate context from partial Terraform state rather than
  require outputs that do not exist after a failed apply.
- No other code directories are modified. No Terraform apply/destroy is run by
  the assistant.
- Passed: `task check`, including Terraform schema validation, Ruff, thirteen
  tests, and native Terraform dependency-graph assertions.
- Verified `task --dry down` schedules only initialization and interactive
  destruction; destruction itself was not executed.

## Teardown consistency correction

- The user requested the faster pattern from the document-intelligence
  Taskfile instead of `terraform destroy`.
- `task down` now requests resource-group deletion with `--yes --no-wait`, then
  cleans only this demo's local Terraform state and cache directories.
- Target lookup supports partial state and the already-selected Canada region,
  while verifying that the subscription still matches the tracked group.
- An active Terraform state lock blocks cleanup. Azure request failure leaves
  local state untouched. The committed provider lock file is retained.
- No cleanup command is executed by the assistant.
- Local proof: Ruff lint/format checks and sixteen Python/teardown tests passed.
  The teardown tests execute the real Taskfile only in temporary fixtures with a
  fake Azure CLI. Four disabled guards were detected, then restored green.
- Full `task check` could not pass Terraform validation because the local
  provider cache is absent. Providers were not reinstalled, and the unchanged
  infrastructure graph check was not rerun.

## Private Blob correction (initial S2 design, superseded)

- Read-only checks reproduced Blob `403 AuthorizationFailure`. Storage public
  access was disabled by a management-group modify policy despite the original
  public-access request. Search and Foundry public access remained enabled.
- The signed-in Azure CLI identity differed from Terraform's operator role
  principal and lacked Blob data permissions. Deployment, CLI operator, and
  private-job identities are now deliberately separate.
- The user approved private Blob networking, Search S2, a new private runner,
  Terraform generation, and VNet CIDR `10.88.0.0/16`. The existing ignored `.env`
  was updated only for the S2/CIDR choices.
- The approved concrete plan is `.azure/infrastructure-plan.json`. No policy
  exemptions, new deployment, or deletion were performed.
- Added private Blob endpoint/DNS, a separate Search shared private link, and
  VNet-integrated manual Container Apps job with explicit NAT egress and managed
  identity. No custom image build, runtime Python packages, or secrets are used.
- `task setup` approves only its own matching private-link request, waits for
  readiness, checks all execution pages for active runs, starts the worker, and
  requires the cloud-reported execution to succeed. The worker verifies private
  Blob DNS before uploads; network-denial errors fail immediately.
- Local proof: Terraform schema/format checks, Ruff lint/format, and all 35
  tests passed. Twenty-five independent guard mutations produced assertion
  failures; all originals passed after restoration. See `docs/tamper-log.md`.
- The pinned official Azure CLI image tag exists in MCR and the local job-log
  CLI command is available. The image was not run locally; no private runner
  execution, Search S2 capacity, ingestion, or agent integration is claimed live.
- `task --dry up` showed extension dependency handling, preflight, Terraform
  init/validate/apply, private setup, and outputs without executing them.

## Basic Search correction

- The user's S2 update failed with `ServiceQuotaExceeded`. Read-only
  `az search usage list --location canadacentral` confirmed zero quota for S2,
  S3, L1, and L2, while Basic had one service against a limit of 12.
  The generic `az quota list` returned no Search entries; an empty response
  was not treated as unlimited quota.
- The user selected: keep Basic and adapt the private runner to index Blob
  documents instead of using managed Blob ingestion. Approved plan version 2
  preserves the VNet, private endpoint, identity, and existing Task targets.
- Read-only service inspection confirmed the existing Search service remained
  `basic` / `Succeeded` after the failed upgrade. No teardown was performed.
- Defaults and the ignored `.env` now select Basic. Removed the Search shared
  private link, its approval workflow, and Search's Blob-reader assignment.
  Added the runner's explicit Cognitive Services OpenAI User assignment.
- The runner lists/downloads Markdown blobs through the private endpoint,
  chunks content, requests embeddings, and pushes a semantic/vector index.
  A `searchIndex` knowledge source connects it to the unchanged shared KB.
- Refresh validates every upload/delete result, removes obsolete index chunks
  only after successful uploads, and waits for both total and current-run
  counts to match. Blob objects themselves are not deleted.
- Preflight now reads the selected tier's regional Search quota before
  Terraform. Missing, zero, or exhausted quota fails explicitly; an existing
  same-tier service can be retried without requiring an extra service slot.
- Passed: `task check`, all 39 tests, and `git diff --check`.
  Approved-plan JSON and all 15 logical resource-group/type dependencies
  were checked for missing references and cycles.
- Passed: 25 independent guard mutations produced assertion failures.
  Originals were restored and all 39 tests passed again; details are in
  `docs/tamper-log.md`. No real state or Azure resources were mutated.
- The user must run `task up` to apply the updated role/output configuration
  and exercise live private indexing, Foundry retrieval, and Copilot Studio.
  No live indexing success is claimed.

## Observability addition (approved)

- Requested: connect the project/agent to Application Insights and show
  diagnostics alongside `task ask`.
- Preserve Basic Search, private Blob indexing, existing Task targets, naming,
  keyless authentication, and the `src/foundryiq` boundary.
- Proposed infrastructure: workspace-backed Application Insights in the
  existing Canada Central resource group/subscription, 30-day retention and
  a 1 GB/day ingestion cap, Entra-only ingestion/query access, project
  managed-identity connection, scoped publisher and query-reader roles.
- Microsoft documents Project Managed Identity for the App Insights connection
  and Monitoring Metrics Publisher for the project identity. The existing
  project's RemoteTool connection confirms that auth representation is accepted
  by its ARM connection API, despite older template enum documentation.
- Terraform owns monitoring resources/RBAC; setup reconciles the App Insights
  project connection alongside the existing MCP connection. No connection
  string, instrumentation key, or credentials are output or packaged.
- Proposed ask output: answer plus response ID, elapsed time, token usage when
  supplied, MCP call details, and correlated server-side telemetry.
- Scope: Foundry server-side agent/model/MCP spans and related events/errors;
  detailed Search resource diagnostics are excluded from this increment.
- Query the App Insights v1 API using Azure CLI Entra tokens; correlate exact
  `gen_ai.response.id` to `operation_Id`, then retrieve that operation's spans
  and logs. Scope queries to 24 hours and the linked App Insights resource.
- Print immediate response diagnostics, then poll for at most 120 seconds
  by default (configurable). Missing telemetry is explicitly pending, never
  presented as a verified trace. API/auth/partial-query errors remain failures.
- Add `task traces -- <response-id>` to query later without invoking the model
  again. No additional application/runtime dependencies or local containers.
- Verify Terraform schema/graph, mocked API payloads/correlation, failure paths,
  and tamper-test changed guards. Commit/push the scoped change.
- Approved: the existing Azure context, these resources and boundaries, and a
  120-second default trace wait. The user runs provisioning and agent calls
  through Task targets. Local checks and code changes are approved.

## Observability preparation results

- Implemented workspace-backed App Insights, 30-day retention, 1 GB/day caps,
  disabled local auth, project publisher RBAC, and operator query RBAC.
- The private setup job reconciles a keyless `AppInsights` project connection.
  Only non-secret resource/application IDs enter outputs and the worker bundle.
- `ask` preserves the full response, prints MCP/request diagnostics, and queries
  exact-response telemetry. `traces` retries queries without invoking the agent.
  Missing records are pending; API/query/agent failures remain failures.
- Passed offline: Terraform schema/format, Ruff, 50 unit/integration-fixture
  tests, Task trace-target dry run, and 23 independent assertion-detected
  mutations. Originals restored; proof is in `docs/tamper-log.md`.
- Read-only regional checks: App Insights advertises Canada Central and this
  subscription has zero regional Log Analytics workspaces. Generic
  `Microsoft.Insights` quota discovery returned `BadRequest`; it does not prove
  unlimited quota or future availability.
- No Azure resources or roles were changed. The new connection payload, trace
  ingestion, and live query correlation still require user-run `task up` and
  `task ask`. Copilot Studio activity traces remain separate.

## Section 7: Validation Proof - observability

- [ ] All validation checks pass (Azure preview/policy/runtime remain user-run).
  - [x] Terraform installation: `terraform version -json` reports 1.16.4.
  - [x] Azure CLI installation: `az version` reports 2.93.0.
  - [x] Authentication: scoped read-only regional resource/provider queries succeeded.
  - [x] Initialize: reused the existing initialized, locked providers; no downloads.
  - [x] Format check: `task check` runs `terraform fmt -check` and Ruff.
  - [x] Validate syntax: `task check` runs `terraform validate`; passed.
  - [ ] Plan preview: reserved for the interactive Terraform apply plan in `task up`.
  - [x] State backend: `terraform -chdir=infra state list` succeeded.
  - [ ] Azure Policy validation: deployment-time checks remain unverified.
  - [x] Template variable resolution: not applicable; plain Terraform, not azd.
- Additional proof: `task check` passed all 50 tests; all 23 isolated mutations
  caused assertion failures without test errors; `git diff --check`, plan JSON
  parsing, `task --list`, and `task --dry traces -- resp_synthetic` passed.
- No Terraform plan/apply, model invocation, role changes, or Azure writes were
  executed by the assistant. Status is not `Validated` for live deployment.

## Role Assignment Verification

- Status: statically verified against the documented service operations.
- Project identity: existing Search reader plus Monitoring Metrics Publisher
  scoped to this App Insights resource, not the account identity.
- CLI operator: existing Blob/Search/Foundry roles plus Log Analytics Reader
  scoped to this App Insights resource and workspace, not the Terraform deployer.
- Setup identity: existing Blob contributor, Search service/index contributor,
  Foundry user/project manager, and OpenAI user roles; reconciles the project
  connection without ingesting/querying agent telemetry itself.
- Search identity: existing OpenAI user role for query vectorization.
- Native Terraform graph checks verify project/publisher/workspace ordering;
  actual assigned-role propagation and trace ingestion remain user-run checks.
