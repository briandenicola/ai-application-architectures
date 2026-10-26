/** Streamable HTTP entry point (stateless: a fresh McpServer per request). */
import { createMcpExpressApp } from "@modelcontextprotocol/express";
import { NodeStreamableHTTPServerTransport } from "@modelcontextprotocol/node";
import cors from "cors";
import type { Request, Response } from "express";
import { createServer } from "./server.js";

const port = parseInt(process.env.PORT ?? "3001", 10);
// Bind to localhost: the SDK then enables DNS-rebinding protection for you.
const app = createMcpExpressApp({ host: "127.0.0.1" });
app.use(cors());

app.all("/mcp", async (req: Request, res: Response) => {
  const server = createServer();
  const transport = new NodeStreamableHTTPServerTransport({ sessionIdGenerator: undefined });
  res.on("close", () => {
    transport.close().catch(() => {});
    server.close().catch(() => {});
  });
  try {
    await server.connect(transport);
    await transport.handleRequest(req, res, req.body);
  } catch (error) {
    console.error("MCP error:", error);
    if (!res.headersSent) {
      res.status(500).json({ jsonrpc: "2.0", error: { code: -32603, message: "Internal server error" }, id: null });
    }
  }
});

app.listen(port, "127.0.0.1", (err?: Error) => {
  if (err) { console.error(`[mcp] cannot listen on ${port}:`, err.message); process.exit(1); }
  console.log(`[mcp] banking MCP server on http://localhost:${port}/mcp`);
});
