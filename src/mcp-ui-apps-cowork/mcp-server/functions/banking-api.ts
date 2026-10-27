import { z } from "zod";
import { demoBanking, holdInputSchema, type HoldRequest } from "../banking.js";
import { HttpError } from "./auth.js";

export type HoldRecorder = (hold: HoldRequest, submittedBy: { kind: "anonymous-demo" }) => Promise<void>;

export async function handleBanking(
  request: Request,
  record: HoldRecorder,
): Promise<Response> {
  const url = new URL(request.url);
  if (request.method === "GET" && url.pathname === "/wires") {
    const minRisk = z.coerce.number().min(0).max(100).safeParse(url.searchParams.get("minRisk") ?? 80);
    if (!minRisk.success) throw new HttpError(400, "minRisk must be a number from 0 to 100");
    return Response.json(await demoBanking.getWires(minRisk.data));
  }
  const wireId = /^\/wires\/([^/]+)$/.exec(url.pathname)?.[1];
  if (request.method === "GET" && wireId) {
    const wire = await demoBanking.getWire(decodeURIComponent(wireId));
    if (!wire) throw new HttpError(404, "Unknown wire");
    return Response.json(wire);
  }
  if (request.method === "POST" && url.pathname === "/holds") {
    let body: unknown;
    try { body = await request.json(); } catch { throw new HttpError(400, "Expected a JSON hold request"); }
    const input = holdInputSchema.safeParse(body);
    if (!input.success) throw new HttpError(400, "A wireId and a non-empty reason of at most 1000 characters are required");
    if (!await demoBanking.getWire(input.data.wireId)) throw new HttpError(404, "Unknown wire");
    const hold = await demoBanking.createHold(input.data);
    await record(hold, { kind: "anonymous-demo" });
    return Response.json(hold, { status: 201 });
  }
  throw new HttpError(404, "Unknown banking operation");
}
