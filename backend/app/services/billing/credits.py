# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
"""Credit accounting: balances, an append-only ledger, and hold/settle for LLM calls.

Concurrency: balances use optimistic locking (``version``), so it behaves the same on SQLite and
Postgres. Every mutation writes the ledger rows and the new balance in a single transaction.

A managed LLM call is  reserve() -> [stream] -> settle():
  * reserve debits the worst-case cost up front (subscription credits first, then purchased);
  * settle refunds the unused part of the hold to the buckets it came from.
"""
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable, Optional

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CreditBalance, CreditLedger, UsageEvent
from app.db.session import Database

log = logging.getLogger(__name__)

SUB, PUR = "subscription", "purchased"
MAX_RETRIES = 12


class InsufficientCredits(Exception):
    def __init__(self, needed: int, available: int):
        super().__init__(f"Insufficient credits: {available} available, {needed} needed")
        self.needed, self.available = needed, available


class ConcurrentUpdate(Exception):
    """Another transaction changed the balance first; the caller must retry from scratch."""


@dataclass(frozen=True)
class Balance:
    subscription: int
    purchased: int

    @property
    def total(self) -> int:
        return self.subscription + self.purchased

    def as_dict(self) -> dict:
        return {"subscription": self.subscription, "purchased": self.purchased, "total": self.total}


async def _load(session: AsyncSession, user_id: int) -> CreditBalance:
    row = (await session.execute(select(CreditBalance).where(CreditBalance.user_id == user_id))).scalar_one_or_none()
    if row is not None:
        return row
    try:
        async with session.begin_nested():
            row = CreditBalance(user_id=user_id, subscription_credits=0, purchased_credits=0, version=0)
            session.add(row)
            await session.flush()
    except IntegrityError as e:  # created concurrently
        raise ConcurrentUpdate from e
    return row


async def apply_changes(session: AsyncSession, user_id: int, changes: list[tuple[str, int, str, Optional[str]]]) -> Balance:
    """Apply ``(bucket, delta, reason, ref)`` rows to the balance and the ledger.

    Raises ConcurrentUpdate when the balance moved under us, InsufficientCredits if a bucket would go negative.
    """
    bal = await _load(session, user_id)
    sub, pur = bal.subscription_credits, bal.purchased_credits
    for bucket, delta, _, _ in changes:
        if bucket == SUB:
            sub += delta
        else:
            pur += delta
    if sub < 0 or pur < 0:
        raise InsufficientCredits(-min(sub, pur), max(0, bal.subscription_credits + bal.purchased_credits))
    result = await session.execute(
        update(CreditBalance)
        .where(CreditBalance.user_id == user_id, CreditBalance.version == bal.version)
        .values(subscription_credits=sub, purchased_credits=pur, version=bal.version + 1)
        .execution_options(synchronize_session=False))
    if result.rowcount != 1:
        raise ConcurrentUpdate
    for bucket, delta, reason, ref in changes:
        if delta != 0:
            session.add(CreditLedger(user_id=user_id, bucket=bucket, delta=delta, reason=reason, ref=ref))
    await session.flush()
    return Balance(sub, pur)


async def read_balance(session: AsyncSession, user_id: int) -> Balance:
    row = (await session.execute(select(CreditBalance).where(CreditBalance.user_id == user_id))).scalar_one_or_none()
    return Balance(row.subscription_credits, row.purchased_credits) if row else Balance(0, 0)


async def retrying(db: Database, work: Callable[[AsyncSession], Awaitable]):
    """Run ``work(session)`` in a transaction, retrying on optimistic-lock conflicts."""
    for attempt in range(MAX_RETRIES):
        try:
            async with db.session() as session:
                return await work(session)
        except ConcurrentUpdate:
            log.debug("credit balance conflict, retry %d", attempt + 1)
    raise RuntimeError("Could not update the credit balance: too much contention")


# ---- operations usable inside a caller's transaction (webhooks) ---------------------------------

async def add_purchased(session: AsyncSession, user_id: int, credits: int, ref: str) -> Balance:
    return await apply_changes(session, user_id, [(PUR, credits, "topup", ref)])


async def grant_subscription(session: AsyncSession, user_id: int, credits: int, ref: str) -> Balance:
    """Start of a paid period: leftover subscription credits expire, the new allowance is granted."""
    bal = await _load(session, user_id)
    changes = []
    if bal.subscription_credits:
        changes.append((SUB, -bal.subscription_credits, "expire", ref))
    changes.append((SUB, credits, "grant", ref))
    return await apply_changes(session, user_id, changes)


async def claw_back_purchased(session: AsyncSession, user_id: int, credits: int, ref: str) -> Balance:
    """Refund of a top-up: remove what is still there (credits already spent stay spent)."""
    bal = await _load(session, user_id)
    take = min(credits, bal.purchased_credits)
    return await apply_changes(session, user_id, [(PUR, -take, "refund", ref)])


class CreditService:
    def __init__(self, db: Database):
        self.db = db

    async def balance(self, user_id: int) -> Balance:
        async with self.db.session() as s:
            return await read_balance(s, user_id)

    async def reserve(self, user_id: int, amount: int, *, analysis_id: Optional[str], provider: str,
                      model: str) -> str:
        """Hold ``amount`` credits and open a usage event. Returns the usage id. Raises InsufficientCredits."""
        usage_id = uuid.uuid4().hex

        async def work(session: AsyncSession) -> str:
            bal = await _load(session, user_id)
            if bal.subscription_credits + bal.purchased_credits < amount:
                raise InsufficientCredits(amount, bal.subscription_credits + bal.purchased_credits)
            from_sub = min(bal.subscription_credits, amount)
            from_pur = amount - from_sub
            await apply_changes(session, user_id, [(SUB, -from_sub, "hold", usage_id), (PUR, -from_pur, "hold", usage_id)])
            session.add(UsageEvent(id=usage_id, user_id=user_id, analysis_id=analysis_id, source="managed",
                                   provider=provider, model=model, hold_subscription=from_sub,
                                   hold_purchased=from_pur, status="pending"))
            return usage_id

        return await retrying(self.db, work)

    async def settle(self, usage_id: str, *, cost: int, input_tokens: int, output_tokens: int,
                     status: str) -> Optional[tuple[Balance, int]]:
        """Charge ``cost`` (capped at the hold), release the rest. Returns (balance, charged); None if already settled."""

        async def work(session: AsyncSession) -> Optional[tuple[Balance, int]]:
            ev = (await session.execute(select(UsageEvent).where(UsageEvent.id == usage_id))).scalar_one_or_none()
            if ev is None or ev.status != "pending":
                return None
            claimed = await session.execute(
                update(UsageEvent).where(UsageEvent.id == usage_id, UsageEvent.status == "pending")
                .values(status=status).execution_options(synchronize_session=False))
            if claimed.rowcount != 1:
                return None
            charge = max(0, min(cost, ev.hold_subscription + ev.hold_purchased))
            used_sub = min(ev.hold_subscription, charge)
            used_pur = charge - used_sub
            balance = await apply_changes(session, ev.user_id, [
                (SUB, ev.hold_subscription - used_sub, "release", usage_id),
                (PUR, ev.hold_purchased - used_pur, "release", usage_id)])
            await session.execute(
                update(UsageEvent).where(UsageEvent.id == usage_id)
                .values(input_tokens=input_tokens, output_tokens=output_tokens, credits_charged=charge,
                        finished_at=datetime.now(timezone.utc))
                .execution_options(synchronize_session=False))
            return balance, charge

        return await retrying(self.db, work)

    async def record_byok(self, user_id: int, *, analysis_id: Optional[str], provider: str, model: str,
                          input_tokens: int, output_tokens: int, status: str) -> None:
        async with self.db.session() as s:
            now = datetime.now(timezone.utc)
            s.add(UsageEvent(id=uuid.uuid4().hex, user_id=user_id, analysis_id=analysis_id, source="byok",
                             provider=provider, model=model, input_tokens=input_tokens,
                             output_tokens=output_tokens, credits_charged=0, status=status, finished_at=now))

    async def reap_stale(self, older_than: timedelta = timedelta(minutes=15)) -> int:
        """Release holds of calls that never settled (process crash, client vanished before streaming)."""
        cutoff = datetime.now(timezone.utc) - older_than
        async with self.db.session() as s:
            ids = (await s.execute(select(UsageEvent.id).where(
                UsageEvent.status == "pending", UsageEvent.created_at < cutoff))).scalars().all()
        for usage_id in ids:
            await self.settle(usage_id, cost=0, input_tokens=0, output_tokens=0, status="aborted")
        return len(ids)
