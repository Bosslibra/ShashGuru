# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
"""Generic OIDC / JWKS bearer-token verifier. Works with Clerk, Auth0, Supabase, Keycloak, ...

Only this adapter package may import ``jwt``; the rest of the application sees ``Identity``.
"""
from typing import Any, Callable, Mapping, Optional

import jwt
from fastapi.concurrency import run_in_threadpool

from app.ports.auth import AuthError, AuthEvent, Identity

ALGORITHMS = ["RS256", "RS384", "RS512", "ES256", "ES384"]


class OidcAuth:
    name = "oidc"

    def __init__(self, *, issuer: str, jwks_url: str = "", audience: str = "", admin_subjects: list[str] | None = None,
                 key_resolver: Optional[Callable[[str], Any]] = None, provider_name: str | None = None):
        if not issuer and not key_resolver:
            raise ValueError("AUTH_ISSUER is required for the oidc/clerk auth provider")
        self.issuer = issuer.rstrip("/")
        self.audience = audience
        self.admin_subjects = set(admin_subjects or [])
        if provider_name:
            self.name = provider_name
        if key_resolver is None:
            client = jwt.PyJWKClient(jwks_url or f"{self.issuer}/.well-known/jwks.json", cache_keys=True,
                                     lifespan=3600, timeout=5)
            key_resolver = lambda token: client.get_signing_key_from_jwt(token).key  # noqa: E731
        self._resolve_key = key_resolver

    def _decode(self, token: str) -> dict:
        key = self._resolve_key(token)
        options = {"require": ["exp", "sub"], "verify_aud": bool(self.audience)}
        return jwt.decode(token, key, algorithms=ALGORITHMS, issuer=self.issuer or None,
                          audience=self.audience or None, leeway=10, options=options)

    async def verify_token(self, token: str) -> Identity:
        try:
            claims = await run_in_threadpool(self._decode, token)
        except jwt.PyJWTError as e:
            raise AuthError(f"Invalid token: {e}") from e
        except Exception as e:  # JWKS endpoint unreachable, etc.
            raise AuthError(f"Token verification failed: {e}") from e
        subject = str(claims["sub"])
        email = claims.get("email")
        return Identity(provider=self.name, subject=subject, email=email if isinstance(email, str) else None,
                        is_admin=subject in self.admin_subjects)

    def parse_webhook(self, headers: Mapping[str, str], body: bytes) -> list[AuthEvent]:
        return []  # generic OIDC providers have no standard lifecycle webhook

    async def delete_identity(self, subject: str) -> None:
        return None  # generic OIDC has no user-management API
