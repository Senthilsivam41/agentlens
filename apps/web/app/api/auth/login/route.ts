import { createHash, randomBytes } from "node:crypto";

import { NextResponse } from "next/server";

function base64url(value: Buffer): string {
  return value.toString("base64url");
}

export async function GET() {
  const issuer = process.env.OIDC_ISSUER;
  const clientId = process.env.OIDC_CLIENT_ID;
  const redirectUri = process.env.OIDC_REDIRECT_URI;
  if (!issuer || !clientId || !redirectUri) {
    return NextResponse.json({ detail: "OIDC not configured" }, { status: 503 });
  }
  const state = base64url(randomBytes(24));
  const verifier = base64url(randomBytes(48));
  const challenge = base64url(createHash("sha256").update(verifier).digest());
  const authorization = new URL(
    process.env.OIDC_AUTHORIZATION_ENDPOINT || `${issuer.replace(/\/$/, "")}/authorize`,
  );
  authorization.search = new URLSearchParams({
    response_type: "code",
    client_id: clientId,
    redirect_uri: redirectUri,
    scope: "openid profile",
    state,
    code_challenge: challenge,
    code_challenge_method: "S256",
  }).toString();
  const response = NextResponse.redirect(authorization);
  const cookie = {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    maxAge: 600,
    path: "/",
  };
  response.cookies.set("agentlens_oidc_state", state, cookie);
  response.cookies.set("agentlens_pkce", verifier, cookie);
  return response;
}
