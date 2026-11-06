# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
"""Wires the application services onto ``app.state`` (used by the lifespan and by the tests)."""
import logging
from typing import Optional

from fastapi import FastAPI

from app.adapters.auth import build_auth
from app.adapters.payments import build_payments
from app.config import Settings
from app.db.session import Database
from app.services.accounts import Accounts
from app.services.analysis_store import AnalysisStore
from app.services.billing.credits import CreditService
from app.services.billing.offers import Offers
from app.services.billing.pricing import Catalog
from app.services.billing.service import BillingService
from app.services.crypto import KeyVault
from app.services.gateway import LLMGateway
from app.services.keys import KeyService
from app.services.providers.openai_compat import OpenAICompatProvider
from app.services.providers.resolver import ProviderRegistry
from app.services.ratelimit import RateLimiter

log = logging.getLogger(__name__)


def build_state(app: FastAPI, settings: Settings, cache, engines, *, db: Optional[Database] = None,
                registry: Optional[ProviderRegistry] = None, auth=None, payments=None) -> None:
    """Create every service. Keyword arguments let tests substitute fakes."""
    state = app.state
    state.settings, state.cache, state.engines = settings, cache, engines
    redis_client = getattr(cache, "client", None)
    state.limiter = RateLimiter(redis_client)
    state.analyses = AnalysisStore(redis_client, settings.analysis_ttl_seconds)
    state.catalog = Catalog.load(settings.models_file)
    state.offers = Offers.load(settings.offers_file)
    state.vault = KeyVault(settings.key_encryption_keys)
    state.auth = auth or build_auth(settings)
    state.payments = payments or build_payments(settings, state.offers)

    if settings.is_saas:
        if not state.vault.configured:
            raise RuntimeError("KEY_ENCRYPTION_KEYS is required in saas mode (see docs/SAAS.md)")
        if settings.cors_origins == ["*"]:
            log.warning("CORS_ORIGINS is '*': set it to your public origin in production")
        state.db = db or Database(settings.database_url)
        state.accounts = Accounts(state.db)
        state.credits = CreditService(state.db)
        state.billing = BillingService(state.db, state.payments, state.offers, settings.public_url)
        state.keys = KeyService(state.db, state.vault)
    else:
        state.db = state.accounts = state.credits = state.billing = state.keys = None

    if registry is None:
        selfhosted = None
        if not settings.is_saas:
            selfhosted = OpenAICompatProvider.create(api_key="unused", base_url=settings.ai_base_url, name="selfhosted",
                                                     include_usage=False)
        registry = ProviderRegistry(settings, state.catalog, state.vault, state.db, selfhosted=selfhosted)
    state.registry = registry
    state.gateway = LLMGateway(settings, state.credits)


async def start_database(app: FastAPI) -> None:
    db: Optional[Database] = app.state.db
    if db is None:
        return
    if app.state.settings.db_auto_create:
        await db.create_all()
    released = await app.state.credits.reap_stale()
    if released:
        log.warning("Released %d stale credit holds", released)


async def stop_services(app: FastAPI) -> None:
    await app.state.registry.close()
    if app.state.db is not None:
        await app.state.db.close()
