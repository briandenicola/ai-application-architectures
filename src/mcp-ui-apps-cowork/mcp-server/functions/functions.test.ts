import assert from "node:assert/strict";
import { test } from "node:test";
import { generateKeyPair, SignJWT } from "jose";
import { demoBanking } from "../banking.js";
import { authenticate, authorizeClaims, HttpError } from "./auth.js";
import { handleBanking } from "./banking-api.js";
import { errorResponse, handleMcp } from "./gateway.js";

const actor = { tenantId: "tenant", objectId: "analyst" };
const userConfig = { tenantId: actor.tenantId, audience: "gateway", kind: "user" as const };

test("Entra authorization rejects wrong tenant, scope, caller, and delegated backend tokens", () => {
  const claims = { tid: "tenant", oid: "analyst", scp: "access_as_user" };
  assert.deepEqual(authorizeClaims(claims, userConfig), actor);
  for (const invalid of [{ ...claims, tid: "other" }, { ...claims, scp: "" }, { ...claims, oid: "" }]) {
    assert.throws(() => authorizeClaims(invalid, userConfig), HttpError);
  }
  const serviceConfig = { ...userConfig, kind: "service" as const, callerId: "gateway-mi" };
  const service = { tid: "tenant", oid: "gateway-object", azp: "gateway-mi", roles: ["Banking.Invoke"] };
  assert.equal(authorizeClaims(service, serviceConfig).objectId, "gateway-object");
  for (const invalid of [
    { ...service, azp: "another-app" }, { ...service, roles: [] }, { ...service, scp: "access_as_user" },
  ]) {
    assert.throws(() => authorizeClaims(invalid, serviceConfig), HttpError);
  }
});

test("authentication validates JWT signature, issuer, audience and expiry, not trusted headers", async () => {
  const { privateKey, publicKey } = await generateKeyPair("RS256");
  const issue = (audience: string, expiry: number, issuer = "https://login.microsoftonline.com/tenant/v2.0",
    signingKey = privateKey) => new SignJWT({
    tid: "tenant", oid: "analyst", scp: "access_as_user",
  }).setProtectedHeader({ alg: "RS256" }).setIssuedAt()
    .setIssuer(issuer)
    .setAudience(audience).setExpirationTime(expiry).sign(signingKey);
  const request = (token: string) => new Request("https://gateway/mcp", {
    headers: { authorization: `Bearer ${token}` },
  });
  const expiry = Math.floor(Date.now() / 1000) + 60;
  assert.deepEqual(await authenticate(request(await issue("gateway", expiry)), userConfig, async () => publicKey), actor);
  const otherKey = await generateKeyPair("RS256");
  for (const token of [
    await issue("other", expiry), await issue("gateway", 1), "not-a-token",
    await issue("gateway", expiry, "https://wrong-issuer.example"),
    await issue("gateway", expiry, undefined, otherKey.privateKey),
  ]) {
    await assert.rejects(authenticate(request(token), userConfig, async () => publicKey), { status: 401 });
  }
  await assert.rejects(authenticate(new Request("https://gateway/mcp", {
    headers: { "x-ms-client-principal": "pretend-identity" },
  }), userConfig), { status: 401 });
});

test("banking records a pending request with actor before reporting success", async () => {
  const records: unknown[] = [];
  const response = await handleBanking(new Request("https://banking/holds", {
    method: "POST", body: JSON.stringify({ wireId: "TX123", reason: "Review beneficiary" }),
  }), actor, async (hold, submittedBy) => { records.push({ hold, submittedBy }); });
  assert.equal(response.status, 201);
  const result = await response.json();
  assert.equal(result.status, "PENDING_APPROVAL");
  assert.equal(records.length, 1);
  assert.deepEqual(records[0], { hold: result, submittedBy: actor });
  await assert.rejects(handleBanking(new Request("https://banking/holds", {
    method: "POST", body: JSON.stringify({ wireId: "TX123", reason: "Review" }),
  }), actor, async () => { throw new Error("storage unavailable"); }), /storage unavailable/);
});

test("invalid or unknown banking requests never create a record", async () => {
  let recorded = false;
  for (const body of [
    JSON.stringify({ wireId: "missing", reason: "Review" }),
    JSON.stringify({ wireId: "TX123", reason: " " }), "invalid JSON",
  ]) {
    await assert.rejects(handleBanking(new Request("https://banking/holds", { method: "POST", body }),
      actor, async () => { recorded = true; }), HttpError);
  }
  await assert.rejects(handleBanking(new Request("https://banking/wires?minRisk=101"),
    actor, async () => {}), { status: 400 });
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

test("stateless MCP gateway preserves UI metadata, result data, resource and app-only callbacks", async () => {
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

test("dependency and authorization failures remain explicit and logged", () => {
  const logged: unknown[] = [];
  assert.equal(errorResponse(new Error("backend failed"), (error) => logged.push(error)).status, 502);
  const rejected = errorResponse(new HttpError(401, "Token required"),
    (error) => logged.push(error), "https://gateway/mcp");
  assert.equal(rejected.status, 401);
  assert.match(rejected.headers.get("www-authenticate")!, /oauth-protected-resource/);
  assert.equal(logged.length, 2);
});
