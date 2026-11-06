# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ai_base_url: str = "http://frontend:6666/v1"
    llm_model: str = "meta-llama/Llama-3.1-8B-Instruct"

    redis_host: str = "redis_cache"
    redis_port: int = 6379

    engine_pool_size: int = 8
    engine_threads: int = 0  # 0 = automatic: cpu_count // pool_size, at least 1
    engine_hash_mb: int = 64
    analysis_timeout: float = 10.0
    engines_dir: Path = BACKEND_DIR / "executables"

    cors_origins: list[str] = ["*"]

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
