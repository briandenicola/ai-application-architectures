/**
 * Host BFF: where the MCP Apps behavior is actually added.
 *
 *   browser ──/api/run──▶ HttpAgent(MAF).use(MCPAppsMiddleware) ──AG-UI──▶ MAF agent (Python)
 *                                  │
 *                                  └──MCP (Streamable HTTP)──▶ banking MCP server
 *
 * The middleware, on each run:
 *   1. lists the MCP server's model-visible tools and adds them to the AG-UI
 *      request as client-side tools,
 *   2. lets MAF run. If the model calls an MCP tool, MAF leaves the call pending,
 *   3. executes the pending call against the MCP server, then emits
 *      TOOL_CALL_RESULT and, for UI tools, an ACTIVITY_SNAPSHOT
 *      (activityType "mcp-apps") carrying { resourceUri, result, toolInput, serverId }.
 *
 * /api/mcp is the same agent+middleware path in "proxied request" mode: the
 * iframe's resources/read and tools/call travel here, and the middleware
 * answers them itself without invoking MAF. This is what CopilotKit's runtime does too.
 */
import { HttpAgent, type BaseEvent, type Message } from "@ag-ui/client";
import { MCPAppsMiddleware } from "@ag-ui/mcp-apps-middleware";
import express from "express";
import { randomUUID } from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";

const PORT = parseInt(process.env.HOST_PORT ?? "3000", 10);
const AGENT_URL = process.env.AGENT_URL ?? "http://localhost:8888/";
const MCP_URL = process.env.MCP_URL ?? "http://localhost:3001/mcp";

// One middleware instance; it opens short-lived MCP connections per operation.
const mcpApps = new MCPAppsMiddleware({
  mcpServers: [{ type: "http", url: MCP_URL, serverId: "banking" }],
});

function newAgent(threadId: string, messages: Message[] = []) {
  return new HttpAgent({ url: AGENT_URL, threadId, initialMessages: messages }).use(mcpApps);
}

const app = express();
app.use(express.json({ limit: "2mb" }));
app.use(express.static(path.join(path.dirname(fileURLToPath(import.meta.url)), "public")));

// Chat turn: stream every AG-UI event to the browser as SSE.
app.post("/api/run", async (req, res) => {
  const { threadId = randomUUID(), messages = [] } = req.body as { threadId?: string; messages?: Message[] };
  res.writeHead(200, { "content-type": "text/event-stream", "cache-control": "no-cache", connection: "keep-alive" });
  const send = (obj: unknown) => res.write(`data: ${JSON.stringify(obj)}\n\n`);

  const agent = newAgent(threadId, messages);
  try {
    await agent.runAgent(
      { runId: randomUUID(), tools: [], context: [] },
      { onEvent: ({ event }: { event: BaseEvent }) => { send(event); } },
    );
    // Hand the browser the full history (incl. tool results) for the next turn.
    send({ type: "HOST_MESSAGES", messages: agent.messages });
  } catch (err) {
    console.error("[host] run failed:", err);
    send({ type: "RUN_ERROR", message: String(err) });
  } finally {
    res.end();
  }
});

// Iframe → host → MCP server, via the middleware's proxied-request mode.
const ALLOWED = new Set(["resources/read", "tools/call"]);
app.post("/api/mcp", async (req, res) => {
  const { serverId, serverHash, method, params } = req.body ?? {};
  if (!ALLOWED.has(method)) return res.status(400).json({ error: `method not allowed: ${method}` });

  let result: unknown;
  const agent = newAgent(randomUUID());
  await agent.runAgent(
    { runId: randomUUID(), forwardedProps: { __proxiedMCPRequest: { serverId, serverHash, method, params } } },
    {
      onEvent: ({ event }: { event: BaseEvent }) => {
        if (event.type === "RUN_FINISHED") result = (event as BaseEvent & { result?: unknown }).result;
      },
    },
  );
  res.json(result ?? { error: "no result" });
});

app.listen(PORT, "127.0.0.1", (err?: Error) => {
  if (err) { console.error(`[host] cannot listen on ${PORT}:`, err.message); process.exit(1); }
  console.log(`[host] http://localhost:${PORT}`);
  console.log(`[host] agent=${AGENT_URL}  mcp=${MCP_URL}`);
});
