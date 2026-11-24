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
  no azd wrapper, containers, web application, or hosted-agent runtime.
- One resource group, one StorageV2 account with a private blob container,
  one Azure AI Search service, one Foundry account, and one Foundry project.
- Search manages ingestion, chunking, and vectorization of the Blob knowledge
  source. One knowledge base exposes retrieval to both agents.
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
  the Foundry prompt agent.
- Principal Task targets: `up`, `ask`, `outputs`, and `check`. `up` includes
  provisioning and setup; `ask` exercises the deployed Foundry agent.

## Execution boundary

Prepare repository files only. Do not build, install dependencies, provision,
invoke Azure services, or delete resources without approval.
Subscription selection, regional model availability, and subscription-specific
quotas must be checked when the user runs the deployment tasks; none have been
queried or asserted available during preparation.

## Approved configuration

- Target region: `eastus2`, configurable in `.env`.
- Authenticated public endpoints for the simple demo, with anonymous blob access
  and local-key authentication disabled; no private networking.
- User-selected region and subscription supplied in an ignored `.env`.
- Local, offline validation approved; all Azure execution remains with the user.
- Use a prompt agent and standard-library Python REST automation, avoiding
  application containers and runtime package installation.

## References

- https://learn.microsoft.com/azure/search/agentic-knowledge-source-how-to-blob
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
