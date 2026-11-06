# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
"""Management of users' own API keys (BYOK). The plaintext key never leaves this module."""
import logging
from typing import Optional

from sqlalchemy import delete, func, select

from app.db.models import ProviderKey
from app.db.session import Database
from app.services.crypto import CryptoError, KeyVault
from app.services.providers.resolver import KEY_PROVIDERS, ResolveError, aad_for, build_user_provider
from app.services.ssrf import UnsafeUrl, assert_public_https_url

log = logging.getLogger(__name__)
MAX_KEYS_PER_USER = 10


def key_out(k: ProviderKey) -> dict:
    return {"id": k.id, "provider": k.provider, "label": k.label, "hint": k.hint, "base_url": k.base_url,
            "created_at": k.created_at.isoformat(), "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None}


class KeyError_(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


class KeyService:
    def __init__(self, db: Database, vault: KeyVault):
        self.db, self.vault = db, vault

    async def list(self, user_id: int) -> list[dict]:
        async with self.db.session() as s:
            rows = (await s.execute(select(ProviderKey).where(ProviderKey.user_id == user_id)
                                    .order_by(ProviderKey.id))).scalars().all()
            return [key_out(r) for r in rows]

    async def add(self, user_id: int, provider: str, api_key: str, label: str = "",
                  base_url: Optional[str] = None) -> dict:
        if provider not in KEY_PROVIDERS:
            raise KeyError_(422, f"Unknown provider '{provider}'")
        api_key = api_key.strip()
        if len(api_key) < 8:
            raise KeyError_(422, "The API key looks too short")
        if provider == "custom":
            try:
                base_url = await assert_public_https_url(base_url or "")
            except UnsafeUrl as e:
                raise KeyError_(422, f"Endpoint rejected: {e}") from e
        else:
            base_url = None
        if not self.vault.configured:
            raise KeyError_(503, "Key storage is not configured on this server")

        try:  # verify before storing: a wrong key is reported now, not at the first analysis
            client = await build_user_provider(provider, api_key, base_url)
            try:
                await client.ping()
            finally:
                await client.close()
        except ResolveError as e:
            raise KeyError_(e.status, e.message) from e
        except Exception as e:
            log.info("BYOK key verification failed for provider %s: %s", provider, type(e).__name__)
            raise KeyError_(422, "The provider rejected this key or endpoint") from e

        ciphertext, nonce, version = self.vault.encrypt(api_key, aad_for(user_id))
        async with self.db.session() as s:
            count = (await s.execute(select(func.count()).select_from(ProviderKey).where(
                ProviderKey.user_id == user_id))).scalar_one()
            if count >= MAX_KEYS_PER_USER:
                raise KeyError_(409, f"You can store at most {MAX_KEYS_PER_USER} keys")
            row = ProviderKey(user_id=user_id, provider=provider, base_url=base_url, ciphertext=ciphertext,
                              nonce=nonce, key_version=version, hint=api_key[-4:], label=label.strip()[:80])
            s.add(row)
            await s.flush()
            return key_out(row)

    async def delete(self, user_id: int, key_id: int) -> bool:
        async with self.db.session() as s:
            result = await s.execute(delete(ProviderKey).where(ProviderKey.id == key_id, ProviderKey.user_id == user_id))
            return result.rowcount > 0

    async def test(self, user_id: int, key_id: int) -> dict:
        async with self.db.session() as s:
            row = (await s.execute(select(ProviderKey).where(
                ProviderKey.id == key_id, ProviderKey.user_id == user_id))).scalar_one_or_none()
            if row is None:
                raise KeyError_(404, "API key not found")
            try:
                api_key = self.vault.decrypt(row.ciphertext, row.nonce, row.key_version, aad_for(user_id))
            except CryptoError:
                return {"ok": False, "message": "The stored key cannot be read: please add it again"}
            provider, base_url = row.provider, row.base_url
        try:
            client = await build_user_provider(provider, api_key, base_url)
            try:
                await client.ping()
            finally:
                await client.close()
        except ResolveError as e:
            return {"ok": False, "message": e.message}
        except Exception:
            return {"ok": False, "message": "The provider rejected this key or endpoint"}
        return {"ok": True}
