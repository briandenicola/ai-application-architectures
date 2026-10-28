import assert from "node:assert/strict";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";
import { demoBanking } from "../banking.js";
import { analyzeWire, remoteBanking } from "./azure-backend.js";

test("the Function entry bundles as Node ESM with the runtime SDK external", async () => {
  const result = await build({
    entryPoints: [fileURLToPath(new URL("./index.ts", import.meta.url))],
    bundle: true, platform: "node", format: "esm", packages: "external", write: false,
  });
  assert.equal(result.errors.length, 0);
  assert.match(result.outputFiles[0].text, /from "@azure\/functions"/);
  assert.match(result.outputFiles[0].text, /import\.meta\.url/);
});

test("gateway calls banking anonymously without requesting an API token or forwarding identity", async (t) => {
  const previous = process.env.BANKING_URL;
  process.env.BANKING_URL = "https://banking.example";
  t.after(() => {
    if (previous === undefined) delete process.env.BANKING_URL;
    else process.env.BANKING_URL = previous;
  });
  const backend = remoteBanking(async (url, init) => {
    const request = new Request(url, init);
    assert.equal(request.headers.has("authorization"), false);
    assert.equal(request.headers.has("x-analyst-object-id"), false);
    if (request.method === "GET") {
      assert.equal(request.url, "https://banking.example/wires?minRisk=80");
      return Response.json(await demoBanking.getWires(80));
    }
    assert.equal(request.url, "https://banking.example/holds");
    const input = await request.json();
    assert.deepEqual(input, { wireId: "TX123", reason: "Review beneficiary" });
    return Response.json(await demoBanking.createHold(input), { status: 201 });
  });
  assert.equal((await backend.getWires(80)).length, 3);
  assert.equal((await backend.createHold({ wireId: "TX123", reason: "Review beneficiary" })).status, "PENDING_APPROVAL");
});

test("investigation calls the persisted Foundry agent with the selected banking record", async (t) => {
  const previous = { endpoint: process.env.FOUNDRY_PROJECT_ENDPOINT, agent: process.env.FOUNDRY_AGENT_NAME };
  process.env.FOUNDRY_PROJECT_ENDPOINT = "https://example.services.ai.azure.com/api/projects/demo";
  process.env.FOUNDRY_AGENT_NAME = "investigator";
  t.after(() => {
    if (previous.endpoint === undefined) delete process.env.FOUNDRY_PROJECT_ENDPOINT;
    else process.env.FOUNDRY_PROJECT_ENDPOINT = previous.endpoint;
    if (previous.agent === undefined) delete process.env.FOUNDRY_AGENT_NAME;
    else process.env.FOUNDRY_AGENT_NAME = previous.agent;
  });
  const wire = (await demoBanking.getWire("TX123"))!;
  const response = {
    status: "completed", output: [{ type: "message", content: [{ type: "output_text", text: "Verify beneficiary details." }] }],
  };
  const result = await analyzeWire(wire, "Explain the signals", {
    credential: { getToken: async (scope) => {
      assert.equal(scope, "https://ai.azure.com/.default");
      return { token: "test-token", expiresOnTimestamp: Date.now() + 60_000 };
    } },
    fetch: async (url, init) => {
      assert.equal(String(url), `${process.env.FOUNDRY_PROJECT_ENDPOINT}/openai/v1/responses`);
      const body = JSON.parse(String(init?.body));
      assert.deepEqual(body.agent_reference, { type: "agent_reference", name: "investigator" });
      assert.deepEqual(JSON.parse(body.input[0].content), { wire, question: "Explain the signals" });
      assert.equal(body.store, false);
      return Response.json(response);
    },
  });
  assert.equal(result, "Verify beneficiary details.");
  for (const payload of [
    { ...response, status: "incomplete" }, { status: "completed", output: [] },
  ]) {
    await assert.rejects(analyzeWire(wire, "Explain", {
      credential: { getToken: async () => ({ token: "test-token", expiresOnTimestamp: Date.now() + 60_000 }) },
      fetch: async () => Response.json(payload),
    }), /not completed|no investigation text/);
  }
  await assert.rejects(analyzeWire(wire, "Explain", {
    credential: { getToken: async () => ({ token: "test-token", expiresOnTimestamp: Date.now() + 60_000 }) },
    fetch: async () => new Response("upstream unavailable", { status: 503 }),
  }), /HTTP 503/);
});
