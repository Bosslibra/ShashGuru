# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(__file__).resolve().parent / "data"

CsvList = Annotated[list[str], NoDecode]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ---- deployment ---------------------------------------------------------
    # selfhosted: no accounts, no billing, LLM = AI_BASE_URL (the historical behaviour)
    # saas:       accounts, BYOK keys, credits, payments
    deployment_mode: Literal["selfhosted", "saas"] = "selfhosted"
    public_url: str = "http://localhost"  # used for checkout redirects
    cors_origins: CsvList = ["*"]
    trust_proxy: bool = False  # honour X-Real-IP / X-Forwarded-For (set behind a reverse proxy)

    # ---- self-hosted LLM ----------------------------------------------------
    ai_base_url: str = "http://frontend:6666/v1"
    llm_model: str = "meta-llama/Llama-3.1-8B-Instruct"

    # ---- engines / cache ----------------------------------------------------
    redis_host: str = "redis_cache"
    redis_port: int = 6379
    engine_pool_size: int = 8
    engine_threads: int = 0  # 0 = automatic: cpu_count // pool_size, at least 1
    engine_hash_mb: int = 64
    analysis_timeout: float = 10.0
    engines_dir: Path = BACKEND_DIR / "executables"

    # ---- database -----------------------------------------------------------
    database_url: str = "sqlite+aiosqlite:///./shashguru.db"
    db_auto_create: bool = False  # create tables at start-up (dev only; production uses Alembic)

    # ---- auth (pluggable) ---------------------------------------------------
    auth_provider: Literal["none", "dev", "oidc", "clerk"] = "none"
    auth_issuer: str = ""
    auth_jwks_url: str = ""  # defaults to <issuer>/.well-known/jwks.json
    auth_audience: str = ""
    auth_admin_subjects: CsvList = []
    auth_webhook_secret: str = ""
    auth_secret_key: str = ""  # provider backend API key, only used to erase users at the provider
    allow_dev_auth: bool = False  # AUTH_PROVIDER=dev is refused in saas mode unless this is set

    # ---- payments (pluggable) -----------------------------------------------
    payment_provider: Literal["none", "stripe"] = "none"
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_automatic_tax: bool = False  # enable once Stripe Tax is configured in the dashboard
    offers_file: Path = DATA_DIR / "offers.yaml"

    # ---- LLM providers ------------------------------------------------------
    models_file: Path = DATA_DIR / "models.yaml"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    openrouter_api_key: str = ""
    credit_markup: float = 1.5  # multiplier applied on top of the provider price
    usd_per_credit: float = 0.001
    max_completion_tokens: int = 1024

    # ---- BYOK encryption: "v2:<base64 key>,v1:<base64 key>", the first one is current ----
    key_encryption_keys: str = ""

    # ---- abuse protection ---------------------------------------------------
    rate_limit_enabled: bool = True
    rate_engine_anon_per_min: int = 60
    rate_engine_user_per_min: int = 180
    rate_game_anon_per_min: int = 4
    rate_game_user_per_min: int = 12
    rate_llm_per_min: int = 15
    anon_max_depth: int = 20
    analysis_ttl_seconds: int = 24 * 3600

    @field_validator("cors_origins", "auth_admin_subjects", mode="before")
    @classmethod
    def _csv(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                import json
                return json.loads(v)
            return [p.strip() for p in v.split(",") if p.strip()]
        return v

    @property
    def is_saas(self) -> bool:
        return self.deployment_mode == "saas"

    @property
    def limits_active(self) -> bool:
        return self.rate_limit_enabled and self.is_saas

    def engine_path(self, name: str) -> str:
        suffix = ".exe" if os.name == "nt" else ""
        return str(self.engines_dir / f"{name}{suffix}")

    @property
    def threads_per_engine(self) -> int:
        if self.engine_threads > 0:
            return self.engine_threads
        return max(1, (os.cpu_count() or 1) // max(1, self.engine_pool_size))


@lru_cache
def get_settings() -> Settings:
    return Settings()
