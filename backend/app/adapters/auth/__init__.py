# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
"""Auth adapters. To support a new identity provider add a module here and a branch in `build_auth`."""
from app.config import Settings
from app.ports.auth import AuthProvider


def build_auth(settings: Settings) -> AuthProvider:
    kind = settings.auth_provider
    if kind == "none":
        from app.adapters.auth.none import NoneAuth
        if settings.is_saas:
            raise RuntimeError("DEPLOYMENT_MODE=saas requires AUTH_PROVIDER to be clerk, oidc or dev")
        return NoneAuth()
    if not settings.is_saas:
        raise RuntimeError("AUTH_PROVIDER other than none requires DEPLOYMENT_MODE=saas")
    if kind == "dev":
        from app.adapters.auth.dev import DevAuth
        if settings.is_saas and not settings.allow_dev_auth:
            raise RuntimeError("AUTH_PROVIDER=dev is insecure: refused in saas mode unless ALLOW_DEV_AUTH=true")
        return DevAuth(settings.auth_admin_subjects)
    common = dict(issuer=settings.auth_issuer, jwks_url=settings.auth_jwks_url, audience=settings.auth_audience,
                  admin_subjects=settings.auth_admin_subjects)
    if kind == "clerk":
        from app.adapters.auth.clerk import ClerkAuth
        return ClerkAuth(webhook_secret=settings.auth_webhook_secret, secret_key=settings.auth_secret_key, **common)
    from app.adapters.auth.oidc import OidcAuth
    return OidcAuth(**common)
