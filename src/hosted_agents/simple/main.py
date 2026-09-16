"""Foundry hosted agent: LangGraph + Toolbox (Bing + SharePoint) + Foundry Memory.

Graph:  recall -> agent <-> tools -> remember

Memory layers:
  short-term  Foundry Responses conversation history (platform-managed; the
              host replays prior turns because this graph has no checkpointer)
  long-term   Foundry Memory store, scoped per end user (x-agent-user-id)

Served by:  python -m langchain_azure_ai.agents.hosting.run --protocol responses
(the runner reads langgraph.json -> main.py:create_graph)
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import re

from azure.ai.agentserver.core import get_request_context
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from langchain_azure_ai.callbacks.tracers.auto_instrument import enable_auto_tracing
from langchain_azure_ai.chat_history import AzureAIMemoryChatMessageHistory
from langchain_azure_ai.tools import AzureAIProjectToolbox
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

load_dotenv()
logging.basicConfig(level=logging.INFO)
# The Azure Monitor exporter logs its own HTTP calls; at INFO those records are
# themselves collected and exported, which loops. Keep the SDK loggers quiet.
for _noisy in ("azure.core.pipeline.policies.http_logging_policy",
               "azure.monitor.opentelemetry.exporter",
               "azure.identity"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)
log = logging.getLogger("demo-agent")

# FOUNDRY_PROJECT_ENDPOINT is injected by the platform (and by `azd ai agent run`).
ENDPOINT = os.environ["FOUNDRY_PROJECT_ENDPOINT"].rstrip("/")
MODEL = os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-5.4-mini")
TOOLBOX = os.environ.get("TOOLBOX_NAME", "demo-tools")
STORE = os.environ.get("MEMORY_STORE_NAME", "demo-memory")
LOCAL_USER = os.environ.get("LOCAL_USER_ID", "local-dev")  # used when no platform user header

_cred = DefaultAzureCredential()


# ---------- tracing -----------------------------------------------------------
def start_tracing() -> None:
    """Send LangGraph/GenAI spans to Application Insights.

    The connection string is resolved from the project's AppInsights connection,
    so no instrumentation key has to live in azure.yaml. Never fatal: a tracing
    problem must not take the agent down.
    """
    try:
        enable_auto_tracing(project_endpoint=ENDPOINT, credential=_cred)
        log.info("tracing enabled -> Application Insights")
    except Exception as e:
        log.warning("tracing disabled (%s): %s", type(e).__name__, e)


start_tracing()

SYSTEM = """You are a concise demo assistant.
- Use web_search for public or current information.
- Use the sharepoint tools for internal company documents and sites.
- When a tool returns URLs, end with a short "Sources" list. Never invent citations.
- If a tool says OAuth consent is required, return the consent URL verbatim.

Long-term memories about this user (may be empty):
{memories}"""


class State(MessagesState):
    memories: str


# ---------- model -------------------------------------------------------------
def build_model() -> ChatOpenAI:
    project = AIProjectClient(endpoint=ENDPOINT, credential=_cred)
    return ChatOpenAI(
        model=MODEL,
        base_url=str(project.get_openai_client().base_url),
        api_key=get_bearer_token_provider(_cred, "https://ai.azure.com/.default"),
        use_responses_api=True,
        output_version="responses/v1",
    )


# ---------- long-term memory (Foundry Memory) --------------------------------
_histories: dict[str, AzureAIMemoryChatMessageHistory] = {}


def memory_scope() -> str:
    # x-agent-user-id: stable per-user ID the platform sets on every hosted request.
    raw = get_request_context().user_id or LOCAL_USER
    return "u-" + hashlib.sha256(raw.encode()).hexdigest()[:32]


def memory_for(scope: str) -> AzureAIMemoryChatMessageHistory:
    if scope not in _histories:
        _histories[scope] = AzureAIMemoryChatMessageHistory(
            STORE,
            scope,
            InMemoryChatMessageHistory(),
            project_endpoint=ENDPOINT,
            credential=_cred,
            update_delay=0,  # demo mode: extract immediately (default waits ~5 min)
        )
    return _histories[scope]


def last_human(state: State) -> HumanMessage:
    return next(m for m in reversed(state["messages"]) if isinstance(m, HumanMessage))


def text_of(msg) -> str:
    c = msg.content
    if isinstance(c, str):
        return c
    return " ".join(p.get("text", "") for p in c if isinstance(p, dict))


# ---------- toolbox tools -----------------------------------------------------
_CONSENT = re.compile(r"https?://[^\s'\"<>)\]]*consent\.azure-api(?:m|hub)\.net[^\s'\"<>)\]]*")


def _tool_error(err: Exception) -> str:
    m = _CONSENT.search(str(err))
    if m or "-32006" in str(err):
        return f"OAuth consent required. Open this URL, approve, then retry: {m.group(0) if m else err}"
    return f"Tool error: {err}"


async def load_tools() -> list[BaseTool]:
    # tools/list fails wholesale if any source is unreachable -- e.g. the
    # SharePoint MCP server rejects callers with no delegated user context.
    # Start with whatever we can get rather than crashing before readiness.
    try:
        tools = await AzureAIProjectToolbox(
            project_endpoint=ENDPOINT, toolbox_name=TOOLBOX
        ).get_tools()
    except Exception as e:
        log.warning("toolbox '%s' unavailable, starting with no tools: %s", TOOLBOX, e)
        return []
    for t in tools:
        t.handle_tool_error = _tool_error
        # Some MCP servers omit "properties" on object schemas, which OpenAI rejects.
        if isinstance(t.args_schema, dict) and t.args_schema.get("type") == "object":
            t.args_schema.setdefault("properties", {})
    log.info("Toolbox '%s' tools: %s", TOOLBOX, [t.name for t in tools])
    return tools


# ---------- graph -------------------------------------------------------------
def build_graph(model: ChatOpenAI, tools: list[BaseTool]):
    llm = model.bind_tools(tools) if tools else model

    async def recall(state: State, config: RunnableConfig):
        retriever = memory_for(memory_scope()).get_retriever(k=5)
        try:
            docs = await retriever.ainvoke(text_of(last_human(state)))
            found = "\n".join(f"- {d.page_content}" for d in docs)
        except Exception as e:  # memory must never take the demo down
            log.warning("memory recall failed: %s", e)
            found = ""
        return {"memories": found or "(none yet)"}

    async def agent(state: State, config: RunnableConfig):
        sys = SystemMessage(SYSTEM.format(memories=state.get("memories", "(none yet)")))
        return {"messages": [await llm.ainvoke([sys, *state["messages"]])]}

    async def remember(state: State, config: RunnableConfig):
        turn = [last_human(state), state["messages"][-1]]
        try:
            await asyncio.to_thread(memory_for(memory_scope()).add_messages, turn)
        except Exception as e:
            log.warning("memory update failed: %s", e)
        return {}

    def route(state: State):
        return "tools" if getattr(state["messages"][-1], "tool_calls", None) else "remember"

    g = StateGraph(State)
    g.add_node("recall", recall)
    g.add_node("agent", agent)
    g.add_node("tools", ToolNode(tools))
    g.add_node("remember", remember)
    g.add_edge(START, "recall")
    g.add_edge("recall", "agent")
    g.add_conditional_edges("agent", route, ["tools", "remember"])
    g.add_edge("tools", "agent")
    g.add_edge("remember", END)
    # No checkpointer on purpose: the Responses host then replays the
    # platform-stored conversation history each turn (durable, no extra infra).
    return g.compile()


async def create_graph():
    """Graph factory referenced by langgraph.json."""
    return build_graph(build_model(), await load_tools())
