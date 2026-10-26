"""A scripted, OpenAI-compatible /v1/chat/completions server for running the demo offline.

It is not a model. It makes the same choices a real model would for this demo,
so you can watch the AG-UI and MCP Apps plumbing without an Azure subscription:

  * last message is from the user, mentions wires/risk, and get_high_risk_wires
    is among the tools  ->  emit a tool call for get_high_risk_wires
  * last message is a tool result  ->  short text acknowledgement
  * anything else  ->  canned text that echoes the user
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI(title="fake-llm")


def _text(msg: dict[str, Any]) -> str:
    c = msg.get("content")
    if isinstance(c, list):
        return " ".join(p.get("text", "") for p in c if isinstance(p, dict))
    return c or ""


def decide(body: dict[str, Any]) -> dict[str, Any]:
    """Return {'text': str} or {'tool': name, 'args': dict}."""
    messages = body.get("messages", [])
    tools = {t["function"]["name"] for t in body.get("tools", []) if t.get("type") == "function"}
    last = messages[-1] if messages else {}
    if last.get("role") == "tool":
        return {"text": "The review panel is up. Select a wire to see its signals or request a hold."}
    user = _text(last).lower()
    wire = re.search(r"\btx\d+\b", user)
    if wire:  # a question about one specific wire -> answer in text
        return {"text": f"{wire.group(0).upper()}: the signals point to elevated fraud and sanctions exposure. "
                        "Recommend escalating to the investigations queue. Any hold stays pending until "
                        "the approval workflow signs off."}
    if "get_high_risk_wires" in tools and re.search(r"wire|risk|flag", user):
        m = re.search(r"(\d{2})", user)
        return {"tool": "get_high_risk_wires", "args": {"minRisk": int(m.group(1)) if m else 80}}
    return {"text": f"(fake LLM) You said: {_text(last)[:120]}"}


def _chunk(cid: str, delta: dict[str, Any], finish: str | None = None) -> str:
    return "data: " + json.dumps({
        "id": cid, "object": "chat.completion.chunk", "created": int(time.time()), "model": "fake-model",
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
    }) + "\n\n"


@app.post("/v1/chat/completions")
async def completions(request: Request):
    body = await request.json()
    d = decide(body)
    cid = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    call_id = f"call_{uuid.uuid4().hex[:12]}"

    if not body.get("stream"):
        msg: dict[str, Any] = {"role": "assistant", "content": d.get("text")}
        if "tool" in d:
            msg["tool_calls"] = [{"id": call_id, "type": "function",
                                  "function": {"name": d["tool"], "arguments": json.dumps(d["args"])}}]
        return JSONResponse({
            "id": cid, "object": "chat.completion", "created": int(time.time()), "model": "fake-model",
            "choices": [{"index": 0, "message": msg, "finish_reason": "tool_calls" if "tool" in d else "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        })

    def gen():
        yield _chunk(cid, {"role": "assistant"})
        if "tool" in d:
            yield _chunk(cid, {"tool_calls": [{"index": 0, "id": call_id, "type": "function",
                                               "function": {"name": d["tool"], "arguments": ""}}]})
            yield _chunk(cid, {"tool_calls": [{"index": 0, "function": {"arguments": json.dumps(d["args"])}}]})
            yield _chunk(cid, {}, "tool_calls")
        else:
            for word in re.findall(r"\S+\s*", d["text"]):
                yield _chunk(cid, {"content": word})
            yield _chunk(cid, {}, "stop")
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("FAKE_LLM_PORT", "8889")))
