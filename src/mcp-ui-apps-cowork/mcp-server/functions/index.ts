import { app, type HttpRequest, type HttpResponseInit, type InvocationContext } from "@azure/functions";
import { ManagedIdentityCredential } from "@azure/identity";
import { BlobServiceClient } from "@azure/storage-blob";
import { readFile } from "node:fs/promises";
import { authenticate, HttpError, type Actor } from "./auth.js";
import { analyzeWire, remoteBanking, required } from "./azure-backend.js";
import { handleBanking } from "./banking-api.js";
import { errorResponse, handleMcp } from "./gateway.js";

const role = required("APP_ROLE");
const tenantId = required("ENTRA_TENANT_ID");
const audience = required("ENTRA_AUDIENCE");
const mcpPublicUrl = () => `https://${required("WEBSITE_HOSTNAME")}/mcp`;

async function toRequest(request: HttpRequest): Promise<Request> {
  return new Request(request.url, {
    method: request.method,
    headers: request.headers,
    body: ["GET", "HEAD"].includes(request.method) ? undefined : await request.text(),
  });
}

async function toResponse(response: Response): Promise<HttpResponseInit> {
  return { status: response.status, headers: Object.fromEntries(response.headers), body: await response.text() };
}

async function handler(request: HttpRequest, context: InvocationContext): Promise<HttpResponseInit> {
  try {
    const incoming = await toRequest(request);
    if (role === "gateway") {
      const actor = await authenticate(incoming, { tenantId, audience, kind: "user" });
      const banking = remoteBanking(actor);
      return toResponse(await handleMcp(incoming, {
        banking,
        readUi: () => readFile(new URL("./wire-review.html", import.meta.url), "utf-8"),
        analyzeWire: async (wireId, question) => {
          const wire = await banking.getWire(wireId);
          if (!wire) throw new HttpError(404, "Unknown wire");
          return analyzeWire(wire, question);
        },
      }));
    }
    await authenticate(incoming, {
      tenantId, audience, kind: "service", callerId: required("GATEWAY_CLIENT_ID"),
    });
    const actor: Actor = {
      objectId: incoming.headers.get("x-analyst-object-id") ?? "",
      tenantId: incoming.headers.get("x-analyst-tenant-id") ?? "",
    };
    if (actor.tenantId !== tenantId || !/^[0-9a-f-]{36}$/i.test(actor.objectId)) {
      throw new HttpError(403, "A trusted analyst identity is required");
    }
    const storage = new BlobServiceClient(required("HOLDS_BLOB_URL"),
      new ManagedIdentityCredential({ clientId: required("AZURE_CLIENT_ID") }));
    return toResponse(await handleBanking(incoming, actor, async (hold, submittedBy) => {
      const blob = storage.getContainerClient("hold-requests").getBlockBlobClient(`${hold.holdRequestId}.json`);
      await blob.uploadData(Buffer.from(JSON.stringify({ ...hold, submittedBy })), {
        conditions: { ifNoneMatch: "*" },
        blobHTTPHeaders: { blobContentType: "application/json" },
      });
      context.log(`Recorded ${hold.holdRequestId}: PENDING_APPROVAL`);
    }));
  } catch (error) {
    return toResponse(errorResponse(error, (cause) => context.error(cause),
      role === "gateway" ? mcpPublicUrl() : undefined));
  }
}

app.setup({ enableHttpStream: true });

if (role === "gateway") {
  app.http("mcp", { route: "mcp", methods: ["GET", "POST", "DELETE"], authLevel: "anonymous", handler });
  app.http("oauth-resource", {
    route: ".well-known/oauth-protected-resource/{*path}",
    methods: ["GET"], authLevel: "anonymous",
    handler: () => ({
      jsonBody: {
        resource: mcpPublicUrl(),
        authorization_servers: [`https://login.microsoftonline.com/${tenantId}/v2.0`],
        scopes_supported: [`api://${audience}/access_as_user`],
        bearer_methods_supported: ["header"],
      },
    }),
  });
} else if (role === "banking") {
  app.http("banking", { route: "{*path}", methods: ["GET", "POST"], authLevel: "anonymous", handler });
} else {
  throw new Error(`Unsupported APP_ROLE ${role}`);
}
