# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
from typing import Awaitable, Callable

from fastapi import Depends, HTTPException, Request

from app.ports.auth import AuthError
from app.services.accounts import LOCAL_PRINCIPAL, Principal, anonymous
from app.services.engine_cache import EngineCache
from app.services.engine_pool import EngineService

UNAUTHORIZED = {"WWW-Authenticate": "Bearer"}


def get_engines(request: Request) -> EngineService:
    return request.app.state.engines


def get_cache(request: Request) -> EngineCache:
    return request.app.state.cache


def client_ip(request: Request) -> str:
    if request.app.state.settings.trust_proxy:
        real = request.headers.get("x-real-ip")
        if real:
            return real.strip()
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[-1].strip()  # the entry appended by our own proxy
    return request.client.host if request.client else "unknown"


async def get_principal(request: Request) -> Principal:
    """The caller: the local admin (self-hosted), a signed-in user, or an anonymous visitor.

    A bearer token that is present but invalid is always a 401, so clients know to refresh it.
    """
    state = request.app.state
    if state.auth.name == "none":
        return LOCAL_PRINCIPAL
    header = request.headers.get("authorization")
    ip = client_ip(request)
    if not header:
        return anonymous(ip)
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(401, "Invalid Authorization header", headers=UNAUTHORIZED)
    try:
        identity = await state.auth.verify_token(token.strip())
    except AuthError as e:
        raise HTTPException(401, str(e), headers=UNAUTHORIZED) from e
    return await state.accounts.principal_for(identity, ip)


async def require_user(principal: Principal = Depends(get_principal)) -> Principal:
    if principal.is_anonymous:
        raise HTTPException(401, "Sign in to continue", headers=UNAUTHORIZED)
    return principal


async def require_account(request: Request, principal: Principal = Depends(require_user)) -> Principal:
    """A real database user: not available on self-hosted deployments (no accounts there)."""
    if not request.app.state.settings.is_saas or principal.user_id is None:
        raise HTTPException(404, "Accounts are not enabled on this deployment")
    return principal


async def require_admin(principal: Principal = Depends(require_user)) -> Principal:
    if not principal.is_admin:
        raise HTTPException(403, "Administrator only")
    return principal


async def saas_only(request: Request) -> None:
    if not request.app.state.settings.is_saas:
        raise HTTPException(404, "Not available on this deployment")


def rate_limited(kind: str) -> Callable[..., Awaitable[Principal]]:
    """Dependency factory: per-user (or per-IP when anonymous) fixed-window limit. ``kind``: engine | game | llm."""

    async def dependency(request: Request, principal: Principal = Depends(get_principal)) -> Principal:
        settings = request.app.state.settings
        if not settings.limits_active:
            return principal
        anon = principal.is_anonymous
        limit = {
            "engine": settings.rate_engine_anon_per_min if anon else settings.rate_engine_user_per_min,
            "game": settings.rate_game_anon_per_min if anon else settings.rate_game_user_per_min,
            "llm": settings.rate_llm_per_min,
        }[kind]
        result = await request.app.state.limiter.hit(f"{kind}:{principal.rate_key}", limit)
        if not result.allowed:
            raise HTTPException(429, "Too many requests, slow down a little",
                                headers={"Retry-After": str(max(1, result.retry_after))})
        return principal

    return dependency
