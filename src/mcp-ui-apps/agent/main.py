"""The harness: a Microsoft Agent Framework agent exposed over AG-UI.

There is NO MCP code here, and that is the point of the sample.

The agent has no tools of its own. On each run, the MCPAppsMiddleware in the
host BFF connects to the MCP server, lists its model-visible tools, and adds
them to the AG-UI request as *client-side* tool declarations. MAF passes them
to the model. When the model calls one, MAF does not execute it: a client-side
tool call ends the run with the call still pending, and the middleware
executes it against the MCP server and emits the result plus an `mcp-apps`
activity that the host renders.

LLM_MODE selects the chat client:
  foundry  (default) FoundryChatClient + az login        FOUNDRY_PROJECT_ENDPOINT, FOUNDRY_MODEL
  azure    Azure OpenAI chat completions + az login      AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT
  fake     scripted local LLM (fake_llm.py), no cloud    FAKE_LLM_URL (default http://localhost:8889/v1)
"""

from __future__ import annotations

import logging
import os

import uvicorn
from agent_framework import Agent
from agent_framework.ag_ui import add_agent_framework_fastapi_endpoint
from dotenv import load_dotenv
from fastapi import FastAPI

# An empty LLM_MODE (e.g. passed through by Taskfile) means "let .env decide".
if not os.environ.get("LLM_MODE"):
    os.environ.pop("LLM_MODE", None)
load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

INSTRUCTIONS = """You are a wire-operations assistant for a bank's payment investigations team.
- When the user asks about risky, flagged, or high-risk wires, call get_high_risk_wires.
  Its results are shown to the user in an interactive panel, so don't repeat the table.
- You cannot approve, release, or hold wires. Holds are requested from the panel and go to
  an approval workflow. Never claim a wire was held or approved.
- Keep answers short."""


def build_client():
    mode = os.getenv("LLM_MODE", "foundry").lower()
    if mode == "fake":
        from agent_framework.openai import OpenAIChatCompletionClient

        return OpenAIChatCompletionClient(
            model="fake-model",
            api_key="not-used",
            base_url=os.getenv("FAKE_LLM_URL", "http://localhost:8889/v1"),
        )
    if mode == "azure":
        from agent_framework.openai import OpenAIChatCompletionClient

        from azure.identity import AzureCliCredential

        return OpenAIChatCompletionClient(
            model=os.environ["AZURE_OPENAI_DEPLOYMENT"],
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
            credential=AzureCliCredential(),
        )
    from agent_framework.foundry import FoundryChatClient
    from azure.identity import AzureCliCredential

    return FoundryChatClient(
        project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        model=os.getenv("FOUNDRY_MODEL", "gpt-4.1"),
        credential=AzureCliCredential(),
    )


agent = Agent(client=build_client(), name="wire-ops", instructions=INSTRUCTIONS)

app = FastAPI(title="MAF AG-UI agent")
# single_user=True is for a local demo only. A shared service must pass an
# authorization_scope_resolver so threads and state are scoped per caller.
add_agent_framework_fastapi_endpoint(app, agent, "/", single_user=True)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "llm_mode": os.getenv("LLM_MODE", "foundry")}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("AGENT_PORT", "8888")))
