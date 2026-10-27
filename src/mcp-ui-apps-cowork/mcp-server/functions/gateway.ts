import { WebStandardStreamableHTTPServerTransport } from "@modelcontextprotocol/server";
import { createServer, type ServerOptions } from "../server.js";
import { HttpError } from "./auth.js";

export async function handleMcp(request: Request, options: ServerOptions): Promise<Response> {
  const server = createServer(options);
  const transport = new WebStandardStreamableHTTPServerTransport({
    sessionIdGenerator: undefined,
    enableJsonResponse: true,
  });
  try {
    await server.connect(transport);
    const response = await transport.handleRequest(request);
    // Consume the response before closing this invocation's stateless transport.
    return new Response(await response.arrayBuffer(), {
      status: response.status, headers: response.headers,
    });
  } finally {
    await server.close();
  }
}

export function errorResponse(error: unknown, log: (error: unknown) => void, resourceUrl?: string): Response {
  log(error);
  const status = error instanceof HttpError ? error.status : 502;
  const headers = new Headers({ "content-type": "application/json" });
  if (status === 401 && resourceUrl) {
    headers.set("www-authenticate",
      `Bearer resource_metadata="${new URL("/.well-known/oauth-protected-resource", resourceUrl)}"`);
  }
  return Response.json({
    error: status === 502 ? "A banking or Foundry dependency failed; no success was recorded" :
      error instanceof Error ? error.message : "Request failed",
  }, { status, headers });
}
