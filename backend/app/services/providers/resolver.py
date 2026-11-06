# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
"""Turns a request (who, which source, which key/model) into a concrete provider + billing mode."""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Optional

from sqlalchemy import select

from app.config import Settings
from app.db.models import ProviderKey, Subscription
from app.db.session import Database
from app.services.accounts import Principal
from app.services.billing.service import ACTIVE_STATUSES
from app.services.billing.pricing import Catalog, ModelEntry
from app.services.crypto import CryptoError, KeyVault
from app.services.providers.anthropic import AnthropicProvider
from app.services.providers.base import LLMProvider
from app.services.providers.openai_compat import OpenAICompatProvider
from app.services.ssrf import UnsafeUrl, assert_public_https_url

OPENROUTER_URL = "https://openrouter.ai/api/v1"
KEY_PROVIDERS = ("openai", "anthropic", "openrouter", "custom")


class ResolveError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


@dataclass
class Resolved:
    provider: LLMProvider
    model: str
    billing: Literal["free", "managed", "byok"]
    provider_name: str
    entry: Optional[ModelEntry] = None
    owned: bool = False  # per-request client that must be closed after use


def aad_for(user_id: int) -> bytes:
    return f"user:{user_id}".encode()


async def build_user_provider(provider: str, api_key: str, base_url: Optional[str]) -> LLMProvider:
    if provider == "anthropic":
        return AnthropicProvider(api_key=api_key)
    if provider == "openai":
        return OpenAICompatProvider.create(api_key=api_key, base_url=None, name="openai")
    if provider == "openrouter":
        return OpenAICompatProvider.create(api_key=api_key, base_url=OPENROUTER_URL, name="openrouter")
    if provider == "custom":
        if not base_url:
            raise ResolveError(422, "This key has no endpoint URL")
        try:
            url = await assert_public_https_url(base_url)
        except UnsafeUrl as e:
            raise ResolveError(422, f"Endpoint rejected: {e}") from e
        return OpenAICompatProvider.create(api_key=api_key, base_url=url, name="custom")
    raise ResolveError(422, f"Unknown provider '{provider}'")


class ProviderRegistry:
    def __init__(self, settings: Settings, catalog: Catalog, vault: KeyVault, db: Optional[Database],
                 selfhosted: Optional[LLMProvider] = None, platform: Optional[dict[str, LLMProvider]] = None):
        self.settings, self.catalog, self.vault, self.db = settings, catalog, vault, db
        self.selfhosted = selfhosted
        self.platform = platform if platform is not None else self._build_platform(settings)

    @staticmethod
    def _build_platform(settings: Settings) -> dict[str, LLMProvider]:
        out: dict[str, LLMProvider] = {}
        if settings.anthropic_api_key:
            out["anthropic"] = AnthropicProvider(api_key=settings.anthropic_api_key)
        if settings.openai_api_key:
            out["openai"] = OpenAICompatProvider.create(api_key=settings.openai_api_key, base_url=None, name="openai")
        if settings.openrouter_api_key:
            out["openrouter"] = OpenAICompatProvider.create(api_key=settings.openrouter_api_key,
                                                            base_url=OPENROUTER_URL, name="openrouter")
        return out

    async def close(self) -> None:
        for p in [self.selfhosted, *self.platform.values()]:
            if p is not None:
                await p.close()

    async def resolve(self, principal: Principal, source: str, key_id: Optional[int], model: Optional[str]) -> Resolved:
        if not self.settings.is_saas:
            if self.selfhosted is None:
                raise ResolveError(503, "No LLM is configured")
            return Resolved(self.selfhosted, self.settings.llm_model, "free", "selfhosted")
        if principal.user_id is None:
            raise ResolveError(401, "Sign in to use the AI analysis")
        if source == "byok":
            return await self._byok(principal.user_id, key_id, model)
        return await self._managed(principal.user_id, model)

    async def _managed(self, user_id: int, model: Optional[str]) -> Resolved:
        model_id = model or self.catalog.default(self.settings)
        entry = self.catalog.get(self.settings, model_id) if model_id else None
        if entry is None:
            raise ResolveError(422, "Unknown or unavailable model")
        provider = self.platform.get(entry.provider)
        if provider is None:
            raise ResolveError(503, "This model is currently unavailable")
        if entry.requires_subscription and not await self._has_subscription(user_id):
            raise ResolveError(402, "This model requires an active subscription")
        if isinstance(provider, AnthropicProvider):
            provider = provider.with_effort(entry.effort)
        return Resolved(provider, entry.id, "managed", entry.provider, entry)

    async def _has_subscription(self, user_id: int) -> bool:
        async with self.db.session() as s:
            sub = await s.get(Subscription, user_id)
        if not sub or sub.status not in ACTIVE_STATUSES:
            return False
        end = sub.current_period_end
        if end is not None and end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        return end is None or end > datetime.now(timezone.utc)

    async def _byok(self, user_id: int, key_id: Optional[int], model: Optional[str]) -> Resolved:
        if key_id is None:
            raise ResolveError(422, "Select one of your API keys")
        if not model:
            raise ResolveError(422, "Choose a model for your API key")
        async with self.db.session() as s:
            row = (await s.execute(select(ProviderKey).where(
                ProviderKey.id == key_id, ProviderKey.user_id == user_id))).scalar_one_or_none()
            if row is None:
                raise ResolveError(404, "API key not found")
            try:
                api_key = self.vault.decrypt(row.ciphertext, row.nonce, row.key_version, aad_for(user_id))
            except CryptoError as e:
                raise ResolveError(500, "Stored API key cannot be read: please add it again") from e
            row.last_used_at = datetime.now(timezone.utc)
            provider_name, base_url = row.provider, row.base_url
        provider = await build_user_provider(provider_name, api_key, base_url)
        return Resolved(provider, model, "byok", provider_name, None, owned=True)
