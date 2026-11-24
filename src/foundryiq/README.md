# Foundry IQ: one handbook, two agents

A small, synthetic employee-handbook demo. Azure Blob Storage supplies the
documents; Foundry IQ manages retrieval; a Foundry agent and a Copilot Studio
agent independently use the same knowledge base.

```mermaid
flowchart LR
    Blob["Azure Blob Storage\n3 synthetic policies"]
    IQ["Foundry IQ / Azure AI Search\nBlob knowledge source + knowledge base"]
    Foundry["Foundry prompt agent"]
    Studio["Copilot Studio agent"]
    Runner["Private setup job\nmanaged identity + VNet"]
    Runner -->|"Blob private endpoint + DNS\nsynthetic policy uploads"| Blob
    Blob -->|"Search shared private link\nmanaged indexing + embeddings"| IQ
    Foundry -->|"MCP + project managed identity"| IQ
    Studio -->|"Native Foundry IQ tool\nEntra ID Integrated"| IQ
```

**No separate application API, API keys, SAS tokens, or storage credentials.**
Blob public access is disabled. A manual Container Apps job uploads and configures
the demo from a private VNet using managed identity; your terminal does not need
a VPN or private Blob connectivity. Search and Foundry retain Entra-authenticated
public endpoints for the Foundry and native Copilot Studio connections.
The handbook is shared demo content: this sample
does not configure per-document permissions or demonstrate employee-specific
authorization.

## What is created

All implementation files and local state stay inside `src/foundryiq`.

| Component | Purpose |
|---|---|
| Terraform in `infra/` | Resource group, private Blob Storage, S2 Search, Foundry account/project, models, RBAC |
| Private setup infrastructure | VNet, delegated runner subnet, separate endpoint subnet, Blob private endpoint/DNS, NAT egress, managed identity, manual Container Apps job |
| `data/*.md` | Fictional leave, expenses, and remote-work policies |
| `scripts/demo.py` | Private-job orchestration, uploads inside the runner, knowledge/agent setup, questions |
| `scripts/runner_bootstrap.py` | Authenticate the job with managed identity and execute the supplied demo bundle |
| `Taskfile.yaml` | Provision/setup, destroy, ask, display endpoints, offline checks |
| [Copilot Studio walkthrough](docs/copilot-studio.md) | Connect the same knowledge base to a second agent |

Search creates and manages the data source, index, indexer, and embedding pipeline
for the Blob knowledge source. Do not separately maintain those generated objects.
The knowledge base uses low-effort model-backed planning and returns extractive
content; each agent composes its own cited answer.

## Prerequisites

- Azure CLI, Terraform 1.6+, Task v3, and Python 3.10+.
- Sign in with `az login` before running the tasks.
- A subscription where you can create resources **and role assignments**.
  Owner, or Contributor plus Role Based Access Control Administrator, is suitable.
  The Azure CLI identity must also be able to start/read the setup job and approve
  the demo's Search-to-Storage private endpoint connection.
  Your organization must allow the required resource providers to be registered.
- A `canadacentral` deployment supporting the selected models and agentic retrieval.
  The region, model versions, deployment SKUs, and capacities are configurable.
- Copilot Studio access and permission to create an agent and its connection in
  your Power Platform environment.
- Ruff for `task check` only; no Python runtime packages are required.
- `task up` checks for the Azure CLI `containerapp` extension and installs it if
  missing. The worker uses the pinned official Azure CLI image, not a local build.

Private managed Blob ingestion requires **Search S2 or higher**. This demo defaults
to S2; Basic and S1 are not supported for that path. S2, NAT Gateway, and private
endpoints add charges even when the setup job is idle. The job itself runs only
when started. This is a disposable single-region demo, not an HA architecture or
an all-services-private deployment. Console logs are fetched after each execution;
no persistent Log Analytics workspace or keys are introduced.

The defaults are `gpt-5.4-mini` version `2026-03-17` (`GlobalStandard`) and
`text-embedding-3-small` version `1` (`GlobalStandard`). `task up` checks the selected
subscription's regional model catalog before provisioning. Catalog presence is
not a quota or capacity guarantee; deployment reports those errors explicitly.
GlobalStandard is a global deployment SKU, not a regional data-residency promise.

## Run

From `src/foundryiq`:

1. Copy `.env.example` to `.env`. Set `AZURE_SUBSCRIPTION_ID`; keep
   `AZURE_LOCATION=canadacentral` or choose another supported region. Set model
   overrides in the same file if needed.
   `TF_VAR_network_address_space` supplies the isolated VNet CIDR; the first two
   `/27` subnets are derived from it. Network addresses are not hardcoded in Terraform.
2. Run:

   ```bash
   task up
   ```

   Review Terraform's plan and enter `yes` to provision. The task then approves
   only this demo's Search-to-Blob shared private link and starts the private job.
   The job verifies private Blob DNS before any upload, then uploads
   the policies, creates the Blob knowledge source, waits for successful
   ingestion, creates the knowledge base and managed-identity MCP connection,
   and creates the Foundry prompt agent. On later setup runs, it creates a new
   version of that agent. Initial provisioning and indexing can take several
   minutes. Indexing polls every five minutes. Terraform creates the Foundry
   project, chat deployment, and embedding deployment sequentially because those
   writes lock the same Foundry account.

   If upgrading an earlier copy, set these values in the existing `.env` before
   running `task up`:

   ```dotenv
   TF_VAR_search_sku=standard2
   TF_VAR_network_address_space=10.88.0.0/16
   ```

   Review any Search replacement in Terraform's plan. Do not use `task setup`
   alone until the new private runner and networking have been provisioned.

3. Ask the Foundry agent:

   ```bash
   task ask -- "How many days of annual leave do I get, and what can I carry over?"
   task ask -- "Can I work remotely four days a week, and claim a $450 monitor?"
   task ask -- "What is the parental leave entitlement?"
   ```

4. Run `task outputs`, then follow [Connect Copilot Studio](docs/copilot-studio.md).
   Ask the same questions in Copilot Studio to demonstrate reuse.

No commands in this sample are run against Azure automatically by a coding
assistant; the tasks are for you to execute.

## Destroy or change region

```bash
task down
```

This follows the document-intelligence Taskfile's fast cleanup pattern:
`az group delete --yes --no-wait`, followed by local Terraform state and cache
cleanup. The resource group is read from state, including after a partial apply.
Azure continues deleting the group in the background. Agents, knowledge bases,
and uploaded data are removed with their parent services.
Deleting the Container Apps environment also removes its provider-managed
infrastructure resource group; the task does not directly delete managed groups.

Cleanup stops if Terraform has an active state lock, the selected subscription
does not match state, or Azure rejects the deletion request. Local state is
removed only after Azure accepts the request. The committed provider lock file
is retained.

To move an existing deployment to Canada Central, run `task down` **before**
`task up`. Set these values in `.env` for the new deployment:

```dotenv
AZURE_LOCATION=canadacentral
TF_VAR_embedding_model_sku=GlobalStandard
```

Then run `task up`. The region guard blocks provisioning over a state that still
contains the old region's resource group. Keep the same subscription selected
while deleting the old deployment. Canada Central advertises GlobalStandard,
not regional Standard, for this embedding model. Search service capacity can
still change between checking regional support and provisioning.

## Demo talk track

| Question | Expected grounded facts |
|---|---|
| Annual leave and carryover? | 20 working days; carry over up to 5; use carryover by March 31 |
| Four remote days and a $450 monitor? | More than 3 remote days requires manager + HR approval; equipment allowance is $400/year with manager pre-approval; the policy does not promise reimbursement above the limit |
| $210 hotel and $80 dinner? | Hotel limit $180/night before tax, with director pre-approval above the limit; meals $65/day on approved overnight travel |
| Parental leave entitlement? | Not defined in the handbook; the agent should say it does not know |

Point out document citations in each answer. In Foundry, open the generated
project in [the Foundry portal](https://ai.azure.com), select
`employee-handbook-agent`, and inspect its MCP tool and conversation trace.
`task ask` fails if the response does not complete, returns a tool error, or
contains no MCP call. It does not evaluate answer correctness or prove citation
accuracy; check the cited policy against the table above.

For a refresh demo, edit an existing policy in `data/`, run `task setup`, and ask
both agents about the new value in fresh conversations. `setup` waits for an
ingestion run started after the uploads, rather than accepting an older success.
It overwrites matching blobs but does **not** delete blobs if a local file is
removed. `task down` removes the entire deployment, not individual documents.

## Authentication and permissions

| Identity | Scope | Role |
|---|---|---|
| Search system identity | Storage account | Storage Blob Data Reader |
| Search system identity | Foundry account hosting the models | Cognitive Services OpenAI User |
| Foundry project system identity | Search service | Search Index Data Reader |
| Azure CLI demo operator | Handbook container | Storage Blob Data Contributor |
| Azure CLI demo operator | Search service | Search Service Contributor + Search Index Data Contributor |
| Azure CLI demo operator | Foundry account | Foundry User + Foundry Project Manager |
| Setup job managed identity | Handbook container | Storage Blob Data Contributor |
| Setup job managed identity | Search service | Search Service Contributor + Search Index Data Contributor |
| Setup job managed identity | Foundry account | Foundry User + Foundry Project Manager |

`task up` derives the operator object ID from the selected Azure CLI token.
Terraform's deployment service principal can be different; its identity is not
silently reused for operator permissions. The private job signs in with its own
user-assigned managed identity. Only the sample script, synthetic policy files,
and non-secret configuration are sent to the job: never `.env`, Terraform state,
Azure CLI caches, or access tokens.

The connection uses `ProjectManagedIdentity` with the Search audience.
The Blob knowledge source's API field is named `connectionString`, but its value
is only `ResourceId=<storage ARM ID>`: no credential is used or output.
Terraform state is local and can contain provider-managed sensitive attributes;
it and `.env` are ignored. Do not share state files. Naming matches the existing
Foundry infrastructure: `${random_pet.this.id}-${random_id.this.dec}` is the base,
with `-foundry`, `-project`, and `-ai_rg` suffixes. Search uses
`${project_name}-search`; Storage uses 22 UUID hex characters followed by `sa`.

## Troubleshooting

| Symptom | Action |
|---|---|
| Model/SKU not advertised | Change model name/version/SKU or region in `.env` **before the first deployment**, then rerun `task up` |
| Insufficient quota or unavailable capacity | Adjust deployment capacities or request quota; rerun `task up` |
| Search reports regional capacity exhaustion | Choose another supported region; use `task down` first if moving an existing deployment |
| Blob `403 AuthorizationFailure` | A network block, not a generic RBAC wait: check the runner's private endpoint/DNS. The script fails immediately and shows the request URL and server error |
| Other setup 401/403 | Confirm the correct runtime identity and roles above; propagation retries are bounded and show method, endpoint, and error detail |
| Private Blob DNS check fails | Check the private DNS zone, VNet link, and Blob endpoint; the worker rejects public or mixed DNS answers |
| Search shared link stays pending | Inspect the target Storage connection. Only the connection matching this demo's unique request message is approved; unrelated requests are never approved |
| Private setup job fails | `task setup` prints that execution's console logs and returns failure; correct the reported cause and rerun it |
| Setup execution already active | Wait for that execution; the script refuses to start another known-active setup |
| Indexing fails or processes no documents | Inspect the Blob knowledge source status in Search and its generated indexer's errors; fix the reported Blob/model permission or model configuration, then run `task setup` |
| Ingestion takes too long | Setup stops after 20 minutes with the last status; inspect the indexer before retrying |
| Agent tool call fails | Check the project's Search reader role, managed-identity connection, and MCP endpoint from `task outputs` |
| Blob citation link prompts for access or returns 403 | Documents are private; a citation is not a public download link. Review the matching local policy or open the blob using an authorized identity |
| Region/subscription mismatch with state | Restore the original subscription; `task down` accepts a changed region while targeting the group recorded in state |
| Cleanup reports a Terraform state lock | Finish or stop the running Terraform operation before running `task down` |

Changing the subscription or region in an existing state can replace resources.
Use one copy/state per deployment. Cleanup is explicit through `task down`;
neither `task up` nor the setup script runs cleanup.

## Offline checks

```bash
task check
```

This runs Terraform formatting and schema validation, Ruff, standard-library unit
tests with mocked service calls, and an offline Terraform dependency-graph check. Initialize
providers first with `terraform -chdir=infra init -backend=false` if you have
not run `task up` yet. `task up` also runs `terraform validate` after provider
initialization. Offline checks cannot verify live Azure provisioning, MCP
execution, model capacity, or Copilot Studio integration.

## Microsoft references

- [Foundry IQ overview](https://learn.microsoft.com/azure/foundry/agents/concepts/what-is-foundry-iq)
- [Blob knowledge source](https://learn.microsoft.com/azure/search/agentic-knowledge-source-how-to-blob)
- [Create a knowledge base](https://learn.microsoft.com/azure/search/agentic-retrieval-how-to-create-knowledge-base)
- [Connect a knowledge base to Foundry Agent Service](https://learn.microsoft.com/azure/foundry/agents/how-to/foundry-iq-connect)
- [Connect Foundry IQ in Copilot Studio](https://learn.microsoft.com/microsoft-copilot-studio/agents-experience/foundry-iq-connect)

The sample uses Search REST `2026-11-01-preview` for knowledge source/base and MCP
operations, ARM `2025-10-01-preview` for the remote-tool connection, and Foundry
agent API `v1`. The MCP and remote-tool connection integration includes preview
capabilities. Recheck the linked documentation if those contracts change.
