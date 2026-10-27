import { createRemoteJWKSet, errors, jwtVerify, type JWTPayload, type JWTVerifyGetKey } from "jose";

export class HttpError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
  }
}

export type Actor = { tenantId: string; objectId: string };
export type AuthConfig = {
  tenantId: string;
  audience: string;
  kind: "user" | "service";
  callerId?: string;
};

const keySets = new Map<string, JWTVerifyGetKey>();

export function authorizeClaims(claims: JWTPayload, config: AuthConfig): Actor {
  if (claims.tid !== config.tenantId || typeof claims.oid !== "string" || !claims.oid) {
    throw new HttpError(403, "Token has no authorized tenant identity");
  }
  if (config.kind === "user") {
    if (typeof claims.scp !== "string" || !claims.scp.split(" ").includes("access_as_user")) {
      throw new HttpError(403, "The access_as_user delegated scope is required");
    }
  } else if (
    !config.callerId || claims.azp !== config.callerId ||
    !Array.isArray(claims.roles) || !claims.roles.includes("Banking.Invoke") ||
    claims.scp !== undefined
  ) {
    throw new HttpError(403, "Only the gateway managed identity may invoke banking tools");
  }
  return { tenantId: claims.tid, objectId: claims.oid };
}

export async function authenticate(
  request: Request,
  config: AuthConfig,
  getKey?: JWTVerifyGetKey,
): Promise<Actor> {
  const header = request.headers.get("authorization");
  if (!header?.startsWith("Bearer ")) throw new HttpError(401, "An Entra access token is required");
  const issuer = `https://login.microsoftonline.com/${config.tenantId}/v2.0`;
  if (!keySets.has(config.tenantId)) {
    keySets.set(config.tenantId, createRemoteJWKSet(
      new URL(`https://login.microsoftonline.com/${config.tenantId}/discovery/v2.0/keys`),
    ));
  }
  let claims: JWTPayload;
  try {
    ({ payload: claims } = await jwtVerify(header.slice(7), getKey ?? keySets.get(config.tenantId)!, {
      issuer, audience: config.audience, algorithms: ["RS256"], requiredClaims: ["exp", "iat", "tid", "oid"],
    }));
  } catch (error) {
    if (error instanceof errors.JOSEError && !(error instanceof errors.JWKSTimeout)) {
      throw new HttpError(401, "The Entra access token is invalid or expired");
    }
    throw error;
  }
  return authorizeClaims(claims, config);
}
