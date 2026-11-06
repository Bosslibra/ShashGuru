# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

from app.config import Settings

CHARS_PER_TOKEN = 3.0  # deliberately pessimistic: used for pre-authorisation and missing usage
TYPICAL_INPUT_TOKENS = 1500
TYPICAL_OUTPUT_TOKENS = 300


def estimate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / CHARS_PER_TOKEN))


@dataclass(frozen=True)
class ModelEntry:
    id: str
    label: str
    provider: str
    price_in: float  # USD / 1M tokens
    price_out: float
    effort: Optional[str] = None
    requires_subscription: bool = False


def cost_credits(entry: ModelEntry, input_tokens: int, output_tokens: int, markup: float,
                 usd_per_credit: float) -> int:
    usd = (input_tokens * entry.price_in + output_tokens * entry.price_out) / 1_000_000
    return max(1, math.ceil(usd * markup / usd_per_credit))


class Catalog:
    def __init__(self, managed: list[ModelEntry], default_managed: Optional[str], byok_suggestions: dict):
        self.managed = managed
        self.default_managed = default_managed
        self.byok_suggestions = byok_suggestions

    @classmethod
    def load(cls, path: Path) -> "Catalog":
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        managed = [ModelEntry(id=m["id"], label=m.get("label", m["id"]), provider=m["provider"],
                              price_in=float(m["price_in"]), price_out=float(m["price_out"]),
                              effort=m.get("effort"), requires_subscription=bool(m.get("requires_subscription")))
                   for m in data.get("managed", [])]
        sugg = {k: list(v) for k, v in (data.get("byok_suggestions") or {}).items()}
        for provider in ("openai", "anthropic", "openrouter", "custom"):
            sugg.setdefault(provider, [])
        return cls(managed, data.get("default_managed"), sugg)

    def available(self, settings: Settings) -> list[ModelEntry]:
        keys = {"openai": settings.openai_api_key, "anthropic": settings.anthropic_api_key,
                "openrouter": settings.openrouter_api_key}
        return [m for m in self.managed if keys.get(m.provider)]

    def get(self, settings: Settings, model_id: str) -> Optional[ModelEntry]:
        return next((m for m in self.available(settings) if m.id == model_id), None)

    def default(self, settings: Settings) -> Optional[str]:
        avail = self.available(settings)
        if any(m.id == self.default_managed for m in avail):
            return self.default_managed
        return avail[0].id if avail else None
