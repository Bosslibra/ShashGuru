# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
"""Users: creation on first login, GDPR export and deletion. Knows nothing about vendors."""
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CreditBalance, CreditLedger, ExternalRef, ProviderKey, Subscription, UsageEvent, User
from app.db.session import Database
from app.ports.auth import Identity
from app.ports.payments import PaymentProvider

log = logging.getLogger(__name__)

CACHE_TTL = 60.0


@dataclass(frozen=True)
class Principal:
    """The caller, as the rest of the application sees them."""
    user_id: Optional[int]
    subject: str
    email: Optional[str] = None
    is_admin: bool = False
    is_anonymous: bool = False
    ip: str = ""

    @property
    def rate_key(self) -> str:
        return f"u{self.user_id}" if self.user_id is not None else f"ip:{self.ip}"


LOCAL_PRINCIPAL = Principal(user_id=None, subject="local", is_admin=True)


def anonymous(ip: str) -> Principal:
    return Principal(user_id=None, subject="anonymous", is_anonymous=True, ip=ip)


class Accounts:
    def __init__(self, db: Database, clock=time.monotonic):
        self.db = db
        self._clock = clock
        self._cache: dict[tuple[str, str], tuple[float, Principal]] = {}

    async def principal_for(self, identity: Identity, ip: str = "") -> Principal:
        key = (identity.provider, identity.subject)
        hit = self._cache.get(key)
        if hit and hit[0] > self._clock() and hit[1].is_admin == identity.is_admin:
            return hit[1]
        async with self.db.session() as s:
            user = await self._upsert(s, identity)
            principal = Principal(user.id, user.auth_subject, user.email, user.is_admin or identity.is_admin,
                                  False, ip)
        if len(self._cache) > 10_000:
            self._cache.clear()
        self._cache[key] = (self._clock() + CACHE_TTL, principal)
        return principal

    async def _upsert(self, s: AsyncSession, identity: Identity) -> User:
        query = select(User).where(User.auth_provider == identity.provider, User.auth_subject == identity.subject)
        user = (await s.execute(query)).scalar_one_or_none()
        if user is None:
            try:
                async with s.begin_nested():
                    user = User(auth_provider=identity.provider, auth_subject=identity.subject,
                                email=identity.email, is_admin=identity.is_admin)
                    s.add(user)
                    await s.flush()
            except IntegrityError:  # created by a concurrent request
                user = (await s.execute(query)).scalar_one()
        elif identity.email and identity.email != user.email:
            user.email = identity.email
        return user

    def forget(self, provider: str, subject: str) -> None:
        self._cache.pop((provider, subject), None)

    async def update_email(self, provider: str, subject: str, email: Optional[str]) -> None:
        async with self.db.session() as s:
            user = (await s.execute(select(User).where(
                User.auth_provider == provider, User.auth_subject == subject))).scalar_one_or_none()
            if user is not None and email:
                user.email = email
        self.forget(provider, subject)

    async def delete_by_subject(self, provider: str, subject: str, payments: PaymentProvider) -> bool:
        async with self.db.session() as s:
            user = (await s.execute(select(User).where(
                User.auth_provider == provider, User.auth_subject == subject))).scalar_one_or_none()
            user_id = user.id if user else None
        if user_id is None:
            return False
        await self.delete_user(user_id, payments)
        self.forget(provider, subject)
        return True

    async def delete_user(self, user_id: int, payments: PaymentProvider) -> None:
        """GDPR erasure: keys and personal data go; the anonymised ledger stays for accounting."""
        async with self.db.session() as s:
            user = await s.get(User, user_id)
            if user is None or user.deleted_at is not None:
                return
            sub = await s.get(Subscription, user_id)
            sub_ref = sub.external_ref if sub and sub.status not in ("canceled",) else None
            self.forget(user.auth_provider, user.auth_subject)
            await s.execute(delete(ProviderKey).where(ProviderKey.user_id == user_id))
            await s.execute(delete(ExternalRef).where(ExternalRef.user_id == user_id))
            if sub:
                sub.status, sub.external_ref = "canceled", ""
            user.email = None
            user.is_admin = False
            user.auth_subject = f"deleted:{uuid.uuid4().hex}"
            user.deleted_at = datetime.now(timezone.utc)
        if sub_ref:
            try:
                await payments.cancel_subscription(sub_ref)
            except Exception:  # the account is already gone; flag it loudly for manual follow-up
                log.exception("Could not cancel subscription %s of deleted user %s", sub_ref, user_id)

    async def export(self, user_id: int) -> dict:
        async with self.db.session() as s:
            user = await s.get(User, user_id)
            keys = (await s.execute(select(ProviderKey).where(ProviderKey.user_id == user_id))).scalars().all()
            ledger = (await s.execute(select(CreditLedger).where(CreditLedger.user_id == user_id)
                                      .order_by(CreditLedger.id))).scalars().all()
            usage = (await s.execute(select(UsageEvent).where(UsageEvent.user_id == user_id)
                                     .order_by(UsageEvent.created_at))).scalars().all()
            sub = await s.get(Subscription, user_id)
            bal = await s.get(CreditBalance, user_id)
            return {
                "user": {"id": user.id, "email": user.email, "created_at": user.created_at.isoformat()},
                "api_keys": [{"id": k.id, "provider": k.provider, "label": k.label, "hint": k.hint,
                              "base_url": k.base_url, "created_at": k.created_at.isoformat()} for k in keys],
                "subscription": ({"offer_id": sub.offer_id, "status": sub.status} if sub else None),
                "balance": ({"subscription": bal.subscription_credits, "purchased": bal.purchased_credits}
                            if bal else None),
                "credit_ledger": [{"at": r.created_at.isoformat(), "bucket": r.bucket, "delta": r.delta,
                                   "reason": r.reason} for r in ledger],
                "usage": [{"at": u.created_at.isoformat(), "source": u.source, "provider": u.provider,
                           "model": u.model, "input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
                           "credits": u.credits_charged, "status": u.status} for u in usage],
            }

    async def usage_page(self, user_id: int, limit: int, offset: int) -> tuple[list[UsageEvent], int]:
        async with self.db.session() as s:
            total = (await s.execute(select(func.count()).select_from(UsageEvent).where(
                UsageEvent.user_id == user_id))).scalar_one()
            rows = (await s.execute(select(UsageEvent).where(UsageEvent.user_id == user_id)
                                    .order_by(UsageEvent.created_at.desc()).limit(limit).offset(offset))).scalars().all()
            return list(rows), total

    async def usage_month(self, user_id: int) -> dict:
        start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        async with self.db.session() as s:
            row = (await s.execute(select(
                func.count(UsageEvent.id), func.coalesce(func.sum(UsageEvent.input_tokens), 0),
                func.coalesce(func.sum(UsageEvent.output_tokens), 0), func.coalesce(func.sum(UsageEvent.credits_charged), 0)
            ).where(UsageEvent.user_id == user_id, UsageEvent.created_at >= start,
                    UsageEvent.status != "pending"))).one()
        return {"requests": int(row[0]), "input_tokens": int(row[1]), "output_tokens": int(row[2]), "credits": int(row[3])}

