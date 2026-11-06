# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
"""Commercial offers (data, not code). Provider ids are looked up here, never hard-coded."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass(frozen=True)
class Offer:
    id: str
    kind: str  # subscription | topup
    name: str
    credits: int
    price: float
    currency: str
    external: dict[str, str] = field(default_factory=dict)

    def public(self) -> dict:
        return {"id": self.id, "kind": self.kind, "name": self.name, "credits": self.credits,
                "price": self.price, "currency": self.currency}


class Offers:
    def __init__(self, offers: list[Offer]):
        self._by_id = {o.id: o for o in offers}

    @classmethod
    def load(cls, path: Path) -> "Offers":
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        items = []
        for raw in data.get("offers", []):
            if raw["kind"] not in ("subscription", "topup"):
                raise ValueError(f"Offer {raw.get('id')}: unknown kind '{raw['kind']}'")
            items.append(Offer(id=raw["id"], kind=raw["kind"], name=raw["name"], credits=int(raw["credits"]),
                               price=float(raw["price"]), currency=raw.get("currency", "eur"),
                               external=dict(raw.get("external") or {})))
        return cls(items)

    def all(self) -> list[Offer]:
        return list(self._by_id.values())

    def get(self, offer_id: str) -> Optional[Offer]:
        return self._by_id.get(offer_id)

    def by_external(self, provider: str, external_id: str) -> Optional[Offer]:
        return next((o for o in self._by_id.values() if o.external.get(provider) == external_id), None)
