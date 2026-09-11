# Foundry hosted agent: LangGraph + Toolbox + Memory

```
azure.yaml               project, models, toolbox, agent (azd reads this)
setup_memory.py          one-time Foundry Memory store creation
src/demo-agent/
  main.py                LangGraph graph factory (recall -> agent <-> tools -> remember)
  langgraph.json         points the host at main.py:create_graph
  Dockerfile             container for the hosted runtime (port 8088)
  requirements.txt
```

## 0. Prereqs (do these first; they are the slow part)
- `azd` 1.27.1+, `azd ext install microsoft.foundry`, `azd auth login`, Docker running
- Foundry Project Manager role on the project (needed to deploy hosted agents)
- The presenter account has access to the SharePoint content and the M365 licensing
  Work IQ requires; tenant admin has enabled Work IQ / Agent 365 MCP servers

## 1. Provision project + models
```bash
azd provision
```

## 2. SharePoint connection (user-delegated) + memory store
```bash
azd ai project set <project-endpoint>
azd ai connection create sharepoint-conn \
  --kind remote-tool \
  --target https://agent365.svc.cloud.microsoft/agents/servers/mcp_SharePointRemoteServer \
  --auth-type user-entra-token \
  --audience ea9ffc3e-8a23-4a7d-836d-234d7c7565c1

pip install -r src/demo-agent/requirements.txt
FOUNDRY_PROJECT_ENDPOINT=<project-endpoint> python setup_memory.py
```
Verify the SharePoint server URL against the Work IQ SharePoint entry in the
Foundry Toolkit tool catalog before you rely on it.

## 3. Run the container locally, then deploy
```bash
azd ai agent run                       # builds the Dockerfile, serves :8088
azd ai agent invoke --local "Hello"
azd deploy                             # push image, create hosted agent version
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
Approve it, then retry.

## Swapping short-term memory for a LangGraph checkpointer
The graph has no checkpointer, so the host replays Foundry-stored history.
To demo LangGraph checkpointing instead, compile with
`langchain_azure_ai.agents.hosting.FoundryCheckpointSaver()` (durable).
Don't use `MemorySaver` in a hosted container: state dies on restart/scale-out.
