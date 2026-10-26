#!/usr/bin/env node
/**
 * Smoke test the running stack through the host BFF, with no browser.
 * Checks every hop: MAF tool call → middleware executes it → mcp-apps activity →
 * UI resource read → app-only tool call.
 *
 *   node scripts/verify.mjs [hostUrl]
 */
const HOST = process.argv[2] ?? process.env.HOST_URL ?? "http://localhost:3000";
let failed = false;
const ok = (msg) => console.log(`  ✓ ${msg}`);
const fail = (msg) => { console.log(`  ✗ ${msg}`); failed = true; };

console.log(`Verifying ${HOST}\n`);

// 1. One chat turn over AG-UI
const res = await fetch(`${HOST}/api/run`, {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ messages: [{ id: "u1", role: "user", content: "Show me high-risk wires" }] }),
});
const events = (await res.text())
  .split("\n\n")
  .map((f) => f.replace(/^data: /, "").trim())
  .filter(Boolean)
  .map((d) => JSON.parse(d));
const types = events.map((e) => e.type);
console.log("AG-UI events:", [...new Set(types)].join(" → "), "\n");

const call = events.find((e) => e.type === "TOOL_CALL_START");
call?.toolCallName === "get_high_risk_wires"
  ? ok("MAF agent called get_high_risk_wires (declared as a client tool by the middleware)")
  : fail(`expected a get_high_risk_wires tool call, got ${call?.toolCallName ?? "none"} (LLM_MODE / model config?)`);

types.includes("TOOL_CALL_RESULT")
  ? ok("middleware executed the tool against the MCP server (TOOL_CALL_RESULT)")
  : fail("no TOOL_CALL_RESULT; is the MCP server up?");

const activity = events.find((e) => e.type === "ACTIVITY_SNAPSHOT" && e.activityType === "mcp-apps");
activity
  ? ok(`mcp-apps activity emitted → ${activity.content.resourceUri} (${activity.content.result?.structuredContent?.wires?.length} wires)`)
  : fail("no mcp-apps ACTIVITY_SNAPSHOT");

if (activity) {
  const { serverId, serverHash, resourceUri } = activity.content;
  const mcp = (method, params) =>
    fetch(`${HOST}/api/mcp`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ serverId, serverHash, method, params }),
    }).then((r) => r.json());

  // 2. What the iframe host does first: fetch the UI
  const resource = await mcp("resources/read", { uri: resourceUri });
  const c = resource.contents?.[0];
  c?.mimeType === "text/html;profile=mcp-app" && c.text?.length > 1000
    ? ok(`resources/read returned the UI (${c.mimeType}, ${(c.text.length / 1024).toFixed(0)} KB)`)
    : fail(`resources/read failed: ${JSON.stringify(resource).slice(0, 200)}`);

  // 3. What the "Create hold" button does
  const hold = await mcp("tools/call", { name: "create_hold_request", arguments: { wireId: "TX123" } });
  hold.structuredContent?.status === "PENDING_APPROVAL"
    ? ok(`app-only tool create_hold_request → ${hold.structuredContent.holdRequestId} ${hold.structuredContent.status}`)
    : fail(`create_hold_request failed: ${JSON.stringify(hold).slice(0, 200)}`);
}

console.log(failed ? "\nFAILED" : "\nAll hops OK. Open the host URL in a browser to see the MCP App.");
process.exit(failed ? 1 : 0);
