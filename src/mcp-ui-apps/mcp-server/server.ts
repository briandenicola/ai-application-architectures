/**
 * Banking MCP server — the "MCP App" half of the sample.
 *
 * It registers three things:
 *
 *   1. get_high_risk_wires   model-visible tool. Its _meta.ui.resourceUri points at
 *                            the UI resource below, so a host that understands MCP
 *                            Apps renders that UI with this tool's result.
 *   2. ui://banking/wire-review   the UI resource: a static, pre-built HTML bundle.
 *                            The tool does NOT generate it. It's registered once
 *                            and the host fetches it by URI.
 *   3. create_hold_request   app-only tool (visibility: ["app"]). The model never
 *                            sees it; only the UI can call it, through the host.
 *                            It records *intent* (a hold request), never executes.
 */
import {
  registerAppResource,
  registerAppTool,
  RESOURCE_MIME_TYPE,
} from "@modelcontextprotocol/ext-apps/server";
import { McpServer } from "@modelcontextprotocol/server";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { z } from "zod";

const DIST_DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), "dist");
const WIRE_REVIEW_URI = "ui://banking/wire-review";

// Demo data. In a real system this comes from the wire service.
const WIRES = [
  { id: "TX123", customer: "Contoso Corp", amount: 4_200_000, currency: "USD", destination: "KY", risk: 92,
    signals: ["New beneficiary", "Unusual amount", "High-risk destination"] },
  { id: "TX456", customer: "Fabrikam Ltd", amount: 2_100_000, currency: "USD", destination: "AE", risk: 87,
    signals: ["Velocity spike", "New beneficiary"] },
  { id: "TX789", customer: "Northwind Traders", amount: 8_700_000, currency: "USD", destination: "PA", risk: 84,
    signals: ["Round-dollar amount", "Shell-company indicators"] },
  { id: "TX901", customer: "Woodgrove Bank", amount: 350_000, currency: "USD", destination: "GB", risk: 41,
    signals: [] },
];

export function createServer(): McpServer {
  const server = new McpServer({ name: "banking-mcp-server", version: "1.0.0" });

  // 1. Model-visible tool, linked to a UI resource
  registerAppTool(
    server,
    "get_high_risk_wires",
    {
      title: "Get high-risk wires",
      description:
        "Returns outgoing wires at or above a risk score, for analyst review. " +
        "The results are shown to the user in an interactive review panel.",
      inputSchema: { minRisk: z.number().min(0).max(100).default(80).describe("Minimum risk score (0-100)") },
      _meta: { ui: { resourceUri: WIRE_REVIEW_URI } },
    },
    async ({ minRisk }) => {
      const wires = WIRES.filter((w) => w.risk >= minRisk).sort((a, b) => b.risk - a.risk);
      return {
        // `content` is what the model reads.
        content: [{
          type: "text",
          text: `${wires.length} wires with risk >= ${minRisk}: ` +
            wires.map((w) => `${w.id} (${w.customer}, $${(w.amount / 1e6).toFixed(1)}M, risk ${w.risk})`).join("; "),
        }],
        // `structuredContent` is what the UI renders.
        structuredContent: { minRisk, wires },
      };
    },
  );

  // 2. The UI resource, served as one self-contained HTML file built by Vite
  registerAppResource(
    server,
    "Wire review panel",
    WIRE_REVIEW_URI,
    { mimeType: RESOURCE_MIME_TYPE, description: "Interactive high-risk wire review" },
    async () => {
      const html = await fs.readFile(path.join(DIST_DIR, "wire-review.html"), "utf-8");
      return { contents: [{ uri: WIRE_REVIEW_URI, mimeType: RESOURCE_MIME_TYPE, text: html }] };
    },
  );

  // 3. App-only tool: the UI's "Create hold" button lands here
  registerAppTool(
    server,
    "create_hold_request",
    {
      title: "Create hold request",
      description: "Submits a hold request for a wire. It goes to the approval workflow; it does not hold the wire itself.",
      inputSchema: {
        wireId: z.string(),
        reason: z.string().default("Analyst review from MCP App"),
      },
      _meta: { ui: { visibility: ["app"] } },
    },
    async ({ wireId, reason }) => {
      const wire = WIRES.find((w) => w.id === wireId);
      if (!wire) {
        return { isError: true, content: [{ type: "text", text: `Unknown wire ${wireId}` }] };
      }
      const holdRequest = {
        holdRequestId: `HOLD-${Math.floor(1000 + Math.random() * 9000)}`,
        wireId,
        reason,
        status: "PENDING_APPROVAL", // intent recorded; the workflow decides
        submittedAt: new Date().toISOString(),
      };
      console.log("[mcp] hold request recorded:", holdRequest);
      return {
        content: [{ type: "text", text: `Hold request ${holdRequest.holdRequestId} submitted for ${wireId}` }],
        structuredContent: holdRequest,
      };
    },
  );

  return server;
}
