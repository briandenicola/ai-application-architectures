import { ManagedIdentityCredential } from "@azure/identity";
import { z } from "zod";
import { holdSchema, wireSchema, type BankingBackend, type Wire } from "../banking.js";
import { HttpError } from "./auth.js";

export function required(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`Missing application setting ${name}`);
  return value;
}

const credential = new ManagedIdentityCredential({ clientId: process.env.AZURE_CLIENT_ID });

export function remoteBanking(fetcher: typeof fetch = fetch): BankingBackend {
  async function call(path: string, body?: unknown): Promise<unknown> {
    const response = await fetcher(new URL(path, required("BANKING_URL")), {
      method: body === undefined ? "GET" : "POST",
      headers: {
        "content-type": "application/json",
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(10_000),
    });
    if (response.status === 404) throw new HttpError(404, "Unknown wire");
    if (!response.ok) throw new Error(`Banking Function returned HTTP ${response.status}`);
    return response.json();
  }
  return {
    getWires: async (minRisk) => z.array(wireSchema).parse(await call(`/wires?minRisk=${minRisk}`)),
    getWire: async (wireId) => wireSchema.parse(await call(`/wires/${encodeURIComponent(wireId)}`)),
    createHold: async (input) => holdSchema.parse(await call("/holds", input)),
  };
}

const responseSchema = z.object({
  status: z.string(),
  output: z.array(z.object({
    type: z.string(),
    content: z.array(z.object({ type: z.string(), text: z.string().optional() })).optional(),
  })),
});

export async function analyzeWire(
  wire: Wire,
  question: string,
  dependencies: { credential: Pick<ManagedIdentityCredential, "getToken">; fetch: typeof fetch } = { credential, fetch },
): Promise<string> {
  const token = await dependencies.credential.getToken("https://ai.azure.com/.default");
  const endpoint = `${required("FOUNDRY_PROJECT_ENDPOINT").replace(/\/$/, "")}/openai/v1/responses`;
  const response = await dependencies.fetch(endpoint, {
    method: "POST",
    headers: { authorization: `Bearer ${token.token}`, "content-type": "application/json" },
    body: JSON.stringify({
      agent_reference: { type: "agent_reference", name: required("FOUNDRY_AGENT_NAME") },
      input: [{
        role: "user",
        content: JSON.stringify({ question, wire }),
      }],
      max_output_tokens: 1200,
      store: false,
    }),
    signal: AbortSignal.timeout(25_000),
  });
  if (!response.ok) throw new Error(`Foundry agent returned HTTP ${response.status}`);
  const result = responseSchema.parse(await response.json());
  if (result.status !== "completed") throw new Error(`Foundry response is ${result.status}, not completed`);
  const text = result.output.flatMap((item) => item.type === "message" ?
    item.content?.filter((part) => part.type === "output_text").map((part) => part.text ?? "") ?? [] : [],
  ).join("\n").trim();
  if (!text) throw new Error("Foundry returned no investigation text");
  return text;
}
