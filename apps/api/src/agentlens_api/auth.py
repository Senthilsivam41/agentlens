"""OIDC JWT validation and tenant/role authorization."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, Request, status

from .config import ApiSettings


@dataclass(frozen=True, slots=True)
class Principal:
    subject: str
    tenant_id: str
    roles: frozenset[str]

    def require(self, *allowed: str) -> None:
        if not self.roles.intersection(allowed):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role")


class Authenticator:
    def __init__(self, settings: ApiSettings) -> None:
        self._settings = settings
        self._jwks = jwt.PyJWKClient(settings.oidc_jwks_url) if settings.oidc_jwks_url else None

    async def authenticate(self, authorization: str | None) -> Principal:
        if self._settings.agentlens_auth_mode == "dev":
            return Principal(
                subject="dev-user",
                tenant_id=self._settings.agentlens_dev_tenant_id,
                roles=frozenset(
                    role.strip()
                    for role in self._settings.agentlens_dev_roles.split(",")
                    if role.strip()
                ),
            )
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="missing bearer token",
            )
        if self._jwks is None or not self._settings.oidc_issuer:
            raise HTTPException(status_code=503, detail="OIDC is not configured")
        token = authorization.removeprefix("Bearer ").strip()
        try:
            signing_key = await asyncio.to_thread(self._jwks.get_signing_key_from_jwt, token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256"],
                audience=self._settings.oidc_audience,
                issuer=self._settings.oidc_issuer,
            )
        except jwt.PyJWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid token",
            ) from exc
        tenant_id = claims.get("tenant_id")
        subject = claims.get("sub")
        roles = claims.get("roles", [])
        if not isinstance(tenant_id, str) or not tenant_id or not isinstance(subject, str):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="required claims missing",
            )
        if isinstance(roles, str):
            roles = roles.split()
        if not isinstance(roles, list) or not all(isinstance(role, str) for role in roles):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid roles claim",
            )
        return Principal(subject=subject, tenant_id=tenant_id, roles=frozenset(roles))


async def principal_dependency(
    request: Request, authorization: Annotated[str | None, Header()] = None
) -> Principal:
    authenticator: Authenticator = request.app.state.authenticator
    return await authenticator.authenticate(authorization)


CurrentPrincipal = Annotated[Principal, Depends(principal_dependency)]
