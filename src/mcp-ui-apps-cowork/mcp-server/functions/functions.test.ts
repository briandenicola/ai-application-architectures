import assert from "node:assert/strict";
import { test } from "node:test";
import { demoBanking } from "../banking.js";
import { HttpError } from "./auth.js";
import { handleBanking } from "./banking-api.js";
import { errorResponse, handleMcp } from "./gateway.js";

test("anonymous banking reads require no token and retain risk filtering", async () => {
  const response = await handleBanking(new Request("https://banking/wires?minRisk=80"), async () => {});
  assert.equal(response.status, 200);
  assert.equal((await response.json()).length, 3);
});

test("banking persists anonymous provenance, never caller-claimed identity, before success", async () => {
  const records: unknown[] = [];
  const response = await handleBanking(new Request("https://banking/holds", {
    method: "POST", headers: { "x-analyst-object-id": "pretend-analyst", "x-analyst-tenant-id": "pretend-tenant" },
    body: JSON.stringify({ wireId: "TX123", reason: "Review beneficiary", submittedBy: { objectId: "pretend-analyst" } }),
  }), async (hold, submittedBy) => { records.push({ hold, submittedBy }); });
  assert.equal(response.status, 201);
  const result = await response.json();
  assert.equal(result.status, "PENDING_APPROVAL");
  assert.equal(records.length, 1);
  assert.deepEqual(records[0], { hold: result, submittedBy: { kind: "anonymous-demo" } });
  await assert.rejects(handleBanking(new Request("https://banking/holds", {
    method: "POST", body: JSON.stringify({ wireId: "TX123", reason: "Review" }),
  }), async () => { throw new Error("storage unavailable"); }), /storage unavailable/);
});

test("invalid or unknown banking requests never create a record", async () => {
  let recorded = false;
  for (const body of [
    JSON.stringify({ wireId: "missing", reason: "Review" }),
    JSON.stringify({ wireId: "TX123", reason: " " }), "invalid JSON",
  ]) {
    await assert.rejects(handleBanking(new Request("https://banking/holds", { method: "POST", body }),
      async () => { recorded = true; }), HttpError);
  }
  await assert.rejects(handleBanking(new Request("https://banking/wires?minRisk=101"),
    async () => {}), { status: 400 });
  assert.equal(recorded, false);
});

async function mcp(method: string, params: object = {}) {
  const response = await handleMcp(new Request("https://gateway/mcp", {
    method: "POST", headers: {
      "content-type": "application/json", accept: "application/json, text/event-stream",
    },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }),
  }), {
    banking: demoBanking, readUi: async () => "<html>wire panel</html>",
    analyzeWire: async (wireId) => `Investigation of ${wireId}`,
  });
  assert.equal(response.status, 200);
  return response.json();
}

test("anonymous stateless MCP preserves UI metadata, result data, resource and app-only callbacks", async () => {
  const initialized = await mcp("initialize", {
    protocolVersion: "2025-03-26", capabilities: {}, clientInfo: { name: "test", version: "1" },
  });
  assert.ok(initialized.result.capabilities.tools);
  const tools = (await mcp("tools/list")).result.tools;
  assert.equal(tools.find((tool: { name: string }) => tool.name === "get_high_risk_wires")._meta.ui.resourceUri,
    "ui://banking/wire-review");
  assert.deepEqual(tools.find((tool: { name: string }) => tool.name === "create_hold_request")._meta.ui.visibility, ["app"]);
  const wires = await mcp("tools/call", { name: "get_high_risk_wires", arguments: { minRisk: 80 } });
  assert.equal(wires.result.structuredContent.wires.length, 3);
  const empty = await mcp("tools/call", { name: "get_high_risk_wires", arguments: { minRisk: 100 } });
  assert.equal(empty.result.structuredContent.wires.length, 0);
  const resource = await mcp("resources/read", { uri: "ui://banking/wire-review" });
  assert.equal(resource.result.contents[0].mimeType, "text/html;profile=mcp-app");
  const hold = await mcp("tools/call", {
    name: "create_hold_request", arguments: { wireId: "TX123", reason: "Analyst selected wire" },
  });
  assert.equal(hold.result.structuredContent.status, "PENDING_APPROVAL");
  const analysis = await mcp("tools/call", {
    name: "analyze_wire", arguments: { wireId: "TX123", question: "Explain the signals" },
  });
  assert.match(analysis.result.content[0].text, /Investigation of TX123/);
});

test("dependency and invalid-request failures remain explicit and logged without OAuth challenges", () => {
  const logged: unknown[] = [];
  assert.equal(errorResponse(new Error("backend failed"), (error) => logged.push(error)).status, 502);
  const rejected = errorResponse(new HttpError(400, "Invalid request"), (error) => logged.push(error));
  assert.equal(rejected.status, 400);
  assert.equal(rejected.headers.has("www-authenticate"), false);
  assert.equal(logged.length, 2);
});
