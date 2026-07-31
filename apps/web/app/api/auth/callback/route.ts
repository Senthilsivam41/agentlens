import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const issuer = process.env.OIDC_ISSUER;
  const clientId = process.env.OIDC_CLIENT_ID;
  const clientSecret = process.env.OIDC_CLIENT_SECRET;
  const redirectUri = process.env.OIDC_REDIRECT_URI;
  const code = request.nextUrl.searchParams.get("code");
  const state = request.nextUrl.searchParams.get("state");
  const expectedState = request.cookies.get("agentlens_oidc_state")?.value;
  const verifier = request.cookies.get("agentlens_pkce")?.value;
  if (
    !issuer ||
    !clientId ||
    !redirectUri ||
    !code ||
    !state ||
    state !== expectedState ||
    !verifier
  ) {
    return NextResponse.json({ detail: "invalid OIDC callback" }, { status: 400 });
  }
  const body = new URLSearchParams({
    grant_type: "authorization_code",
    code,
    client_id: clientId,
    redirect_uri: redirectUri,
    code_verifier: verifier,
  });
  if (clientSecret) body.set("client_secret", clientSecret);
  const tokenEndpoint =
    process.env.OIDC_TOKEN_ENDPOINT || `${issuer.replace(/\/$/, "")}/token`;
  const tokenResponse = await fetch(tokenEndpoint, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
    cache: "no-store",
  });
  if (!tokenResponse.ok) {
    return NextResponse.json({ detail: "OIDC token exchange failed" }, { status: 401 });
  }
  const token = (await tokenResponse.json()) as {
    access_token?: string;
    expires_in?: number;
  };
  if (!token.access_token) {
    return NextResponse.json({ detail: "OIDC response missing access token" }, { status: 401 });
  }
  const response = NextResponse.redirect(new URL("/", request.url));
  response.cookies.set("agentlens_access_token", token.access_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: token.expires_in ?? 3600,
    path: "/",
  });
  response.cookies.delete("agentlens_oidc_state");
  response.cookies.delete("agentlens_pkce");
  return response;
}
