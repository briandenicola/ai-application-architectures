# Foundry hosted agent: LangGraph + Toolbox + Memory

All files are flat in this directory — `azure.yaml` sets `project: .`, so the
build context and the Dockerfile are right here.

```
azure.yaml               project, models, toolbox, agent (azd reads this)
setup_memory.py          one-time Foundry Memory store creation
main.py                  LangGraph graph factory (recall -> agent <-> tools -> remember)
langgraph.json           points the host at main.py:create_graph
Dockerfile               container for the hosted runtime (port 8088)
requirements.txt
.env.example             local-run env vars only
.dockerignore            keeps .env / .azure out of the image
```

## 0. Prereqs (do these first; they are the slow part)
- `azd` 1.27.1+ (enforced by `requiredVersions` in azure.yaml), `azd auth login`, Docker running
- `azd ext install microsoft.foundry` — a meta-package that bundles the Foundry
  extensions. azure.yaml specifically requires `azure.ai.agents` >= 1.0.0-beta.9;
  this project also uses the projects, toolboxes, connections, and inspector extensions.
- Foundry Project Manager role on the project (needed to deploy hosted agents)
- The presenter account has access to the SharePoint content and the M365 licensing
  Work IQ requires; tenant admin has enabled Work IQ / Agent 365 MCP servers

Run `azd ai agent doctor` at any point — it checks the azure.yaml, the agent
definition, env vars, auth, role assignment, and connections, and prints a fix
for each failure.

## 1. Provision project + models
```bash
azd provision
```
Creates the project plus the `gpt-5.4-mini` and `text-embedding-3-large`
deployments declared in azure.yaml, and sets `FOUNDRY_PROJECT_ENDPOINT` in the
azd environment.

## 2. SharePoint connection (user-delegated) + memory store
```bash
azd ai project set <project-endpoint>
azd ai connection create sharepoint-conn \
  --kind remote-tool \
  --target https://agent365.svc.cloud.microsoft/agents/servers/mcp_SharePointRemoteServer \
  --auth-type user-entra-token \
  --audience ea9ffc3e-8a23-4a7d-836d-234d7c7565c1

pip install -r requirements.txt
FOUNDRY_PROJECT_ENDPOINT=<project-endpoint> python setup_memory.py
```
`setup_memory.py` is idempotent — it prints "already exists" and makes no changes
on a second run. It reads `MEMORY_STORE_NAME` (default `demo-memory`),
`AZURE_AI_MODEL_DEPLOYMENT_NAME` (default `gpt-5.4-mini`), and
`EMBEDDING_DEPLOYMENT` (default `text-embedding-3-large`), and enables the
user-profile and chat-summary extractors.

Verify the SharePoint server URL against the Work IQ SharePoint entry in the
Foundry Toolkit tool catalog before you rely on it.

## 3. Run the container locally, then deploy
```bash
azd ai agent run                       # builds the Dockerfile, serves :8088
azd ai agent invoke --local "Hello"
azd deploy                             # push image, create hosted agent version
```
`azd ai agent run` also opens the Agent Inspector UI on port 8087; pass
`--no-client` to skip it. Docker must be running for both `run` and `deploy`; if
you can't run Docker locally, add `remoteBuild: true` under a `docker:` section
on the `demo-agent` service to build in Azure instead.

`azd deploy` is also what materializes the toolbox MCP endpoint
(`TOOLBOX_DEMO_TOOLS_MCP_ENDPOINT`) into the azd environment, so `azd ai agent
doctor` reports that check as failing until the first deploy.

## Environment variables
| Variable | Set by | Default in code |
|---|---|---|
| `FOUNDRY_PROJECT_ENDPOINT` | platform / `azd provision` | required, no default |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | azure.yaml | `gpt-5.4-mini` |
| `TOOLBOX_NAME` | azure.yaml | `demo-tools` |
| `MEMORY_STORE_NAME` | azure.yaml | `demo-memory` |
| `EMBEDDING_DEPLOYMENT` | setup_memory.py only | `text-embedding-3-large` |
| `LOCAL_USER_ID` | local runs only | `local-dev` |
| `APPLICATION_INSIGHTS_CONNECTION_STRING` | azd env (gitignored) | falls back to project connection |
| `OTEL_AUTO_CONFIGURE_AZURE_MONITOR` | azure.yaml | `true` |
| `AZURE_TRACING_ALL_LANGGRAPH_NODES` | azure.yaml | `true` |
| `AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED` | azure.yaml | `true` (records content) |

Long-term memory is scoped per end user: `main.py` takes the platform's
`x-agent-user-id`, falls back to `LOCAL_USER_ID` locally, and SHA-256 hashes it
into the memory scope. Recall pulls the top 5 memories per turn, and the history
is created with `update_delay=0` so extraction is immediate instead of the ~5
minute default — demo mode, not a production setting. Memory failures are logged
and swallowed so they can't take the demo down.

## Observability

Everything lands in one Log Analytics workspace (`log-tymqvw2xggqwm`), because the
App Insights component is workspace-based:

| Layer | Wiring | Where it shows up |
|---|---|---|
| Foundry platform | diagnostic setting `foundry-to-la` on the account (`Audit`, `RequestResponse`, `Trace`, `AzureOpenAIRequestUsage`, `AllMetrics`) | `AzureDiagnostics` |
| Project | connection `appi-tymqvw2xggqwm` (`category: AppInsights`) | makes the connection string discoverable to the project |
| Agent container | `enable_auto_tracing()` in `main.py` + the `AZURE_TRACING_*` / `OTEL_*` env vars in azure.yaml | `AppTraces`, `AppDependencies`, `AppRequests` |

Spans include `chat gpt-5.4-mini`, the memory `search_memories` / `update_memories`
calls, and the toolbox MCP round trips, so a single invoke is traceable end to end.

The connection string is read from `APPLICATION_INSIGHTS_CONNECTION_STRING`, set in
the azd environment (`.azure/`, gitignored) rather than committed. If it's ever
unset, `main.py` falls back to resolving it from the project's AppInsights
connection via `project_endpoint` + credential.

`AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED` is `true`, which records prompt
and response content. Good for a demo, but turn it off for anything sensitive.

Handy queries:
```bash
# agent spans
az monitor app-insights query --app appi-tymqvw2xggqwm -g rg-dev-simple \
  --analytics-query "dependencies | where timestamp > ago(1h) | summarize count() by name"

# platform logs
az monitor log-analytics query -w <workspace-guid> \
  --analytics-query "AzureDiagnostics | where TimeGenerated > ago(1h)"
```

## Demo script
| Step | Say | Shows |
|---|---|---|
| 1 | "I'm the Contoso account lead. Keep answers to 3 bullets." | Written to Foundry Memory |
| 2 | "Latest public news on Contoso?" | Toolbox `web_search` (Bing) |
| 3 | "Find the Contoso proposal in SharePoint and summarize it." | Toolbox SharePoint MCP as *you* |
| 4 | "What did I ask two messages ago?" | Short-term: platform conversation history |
| 5 | New conversation: "What do you know about me?" | Long-term: Foundry Memory, per user |

`azd ai agent invoke --new-session --new-conversation "What do you know about me?"`

Rehearse step 3 once: the first SharePoint call returns an OAuth consent URL.
`main.py` detects the consent error and returns the URL verbatim. Approve it,
then retry.

**SharePoint needs a delegated user context.** The connection uses
`user-entra-token`, so a caller with no delegated Entra user identity (a plain
`azd ai agent invoke`, for example) gets `CONNECTION_FAILED` from that MCP
server. `tools/list` fails wholesale when any source is unreachable, so
`load_tools()` degrades to no tools rather than crashing the container before
readiness — watch for `toolbox '...' unavailable` in the logs. Drive step 3 from
the portal playground, or pass `--user-identity`, to exercise SharePoint.

## Swapping short-term memory for a LangGraph checkpointer
The graph has no checkpointer, so the host replays Foundry-stored history.
To demo LangGraph checkpointing instead, compile with `FoundryCheckpointSaver`,
which persists checkpoints in Foundry state stores (durable):

```python
from langchain_azure_ai.agents.hosting._foundry_checkpoint_saver import (
    FoundryCheckpointSaver,
)

g.compile(checkpointer=FoundryCheckpointSaver())
```

It lives in a private module and is not re-exported from
`langchain_azure_ai.agents.hosting`, so this import path can break between
releases (verified against langchain-azure-ai 1.2.9). It is async-only — use
`ainvoke`/`astream`, which this graph already does. It isolates by user and
expires items after 30 days by default.

Don't use `MemorySaver` in a hosted container: state dies on restart/scale-out.
