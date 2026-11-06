# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
"""Billing domain logic. Consumes normalised events from any PaymentProvider."""
import logging
from datetime import datetime, timezone
from typing import Mapping, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CreditLedger, ExternalRef, Subscription, User, WebhookEvent
from app.db.session import Database
from app.ports.payments import (BillingEvent, CheckoutRequest, CustomerLinked, PaymentError, PaymentProvider,
                                Refunded, SubscriptionChanged, SubscriptionRenewed, TopupPaid)
from app.services.billing import credits
from app.services.billing.offers import Offers

log = logging.getLogger(__name__)

ACTIVE_STATUSES = ("active", "trialing", "past_due")


class BillingError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


class BillingService:
    def __init__(self, db: Database, payments: PaymentProvider, offers: Offers, public_url: str):
        self.db, self.payments, self.offers = db, payments, offers
        self.public_url = public_url.rstrip("/")

    # ---- outbound -----------------------------------------------------------------------------

    async def _customer_ref(self, s: AsyncSession, user_id: int) -> Optional[str]:
        return (await s.execute(select(ExternalRef.ref).where(
            ExternalRef.user_id == user_id, ExternalRef.provider == self.payments.name,
            ExternalRef.kind == "customer"))).scalar_one_or_none()

    async def checkout(self, user_id: int, offer_id: str) -> str:
        offer = self.offers.get(offer_id)
        if offer is None:
            raise BillingError("Unknown offer", 404)
        price_id = offer.external.get(self.payments.name)
        if not price_id:
            raise BillingError("This offer is not available with the current payment provider", 400)
        async with self.db.session() as s:
            user = await s.get(User, user_id)
            customer = await self._customer_ref(s, user_id)
            sub = await s.get(Subscription, user_id)
            if offer.kind == "subscription" and sub and sub.status in ACTIVE_STATUSES:
                raise BillingError("You already have an active subscription: manage it from the billing portal", 409)
            email = user.email
        req = CheckoutRequest(user_id, email, offer.id, offer.kind, price_id, customer,
                              success_url=f"{self.public_url}/account?checkout=success",
                              cancel_url=f"{self.public_url}/pricing?checkout=cancelled")
        try:
            return await self.payments.create_checkout(req)
        except PaymentError as e:
            raise BillingError(str(e), 502) from e

    async def portal(self, user_id: int) -> str:
        async with self.db.session() as s:
            customer = await self._customer_ref(s, user_id)
        if not customer:
            raise BillingError("No billing account yet: buy a plan or credits first", 404)
        try:
            return await self.payments.create_portal(customer, f"{self.public_url}/account")
        except PaymentError as e:
            raise BillingError(str(e), 502) from e

    # ---- inbound ------------------------------------------------------------------------------

    async def handle_webhook(self, headers: Mapping[str, str], body: bytes) -> bool:
        """Verify, deduplicate and apply a webhook. Returns False if it was already processed."""
        parsed = self.payments.parse_webhook(headers, body)  # raises PaymentError on a bad signature
        for _ in range(credits.MAX_RETRIES):
            try:
                async with self.db.session() as s:
                    try:  # savepoint: a duplicate must not poison the outer transaction
                        async with s.begin_nested():
                            s.add(WebhookEvent(provider=self.payments.name, event_id=parsed.event_id))
                            await s.flush()
                    except IntegrityError:
                        return False
                    for event in parsed.events:
                        await self._apply(s, event)
                    return True
            except credits.ConcurrentUpdate:
                continue
        raise RuntimeError("Webhook could not be applied: too much contention")

    async def _user_for(self, s: AsyncSession, customer_ref: Optional[str], user_id: Optional[int] = None) -> Optional[int]:
        if user_id:
            return user_id
        if not customer_ref:
            return None
        return (await s.execute(select(ExternalRef.user_id).where(
            ExternalRef.provider == self.payments.name, ExternalRef.kind == "customer",
            ExternalRef.ref == customer_ref))).scalar_one_or_none()

    async def _apply(self, s: AsyncSession, event: BillingEvent) -> None:
        provider = self.payments.name
        if isinstance(event, CustomerLinked):
            exists = (await s.execute(select(ExternalRef.id).where(
                ExternalRef.provider == provider, ExternalRef.kind == "customer",
                ExternalRef.ref == event.customer_ref))).first()
            if not exists and await s.get(User, event.user_id):
                s.add(ExternalRef(user_id=event.user_id, provider=provider, kind="customer", ref=event.customer_ref))
                await s.flush()

        elif isinstance(event, TopupPaid):
            offer = self.offers.get(event.offer_id)
            user_id = await self._user_for(s, event.customer_ref, event.user_id)
            if not offer or not user_id:
                log.error("Top-up %s cannot be applied (offer=%s user=%s)", event.payment_ref, event.offer_id, user_id)
                return
            await credits.add_purchased(s, user_id, offer.credits, event.payment_ref)

        elif isinstance(event, SubscriptionRenewed):
            offer = self.offers.get(event.offer_id)
            user_id = await self._user_for(s, event.customer_ref)
            if not offer or not user_id:
                log.error("Renewal %s cannot be applied (offer=%s customer=%s)", event.invoice_ref, event.offer_id,
                          event.customer_ref)
                return
            await self._upsert_subscription(s, user_id, event.subscription_ref, event.offer_id, "active",
                                            event.period_end)
            await credits.grant_subscription(s, user_id, offer.credits, event.invoice_ref)

        elif isinstance(event, SubscriptionChanged):
            user_id = await self._user_for(s, event.customer_ref)
            if user_id:
                await self._upsert_subscription(s, user_id, event.subscription_ref, event.offer_id, event.status,
                                                event.period_end)

        elif isinstance(event, Refunded):
            row = (await s.execute(select(CreditLedger).where(
                CreditLedger.reason == "topup", CreditLedger.ref == event.payment_ref))).scalars().first()
            if row is None or event.total_amount <= 0:
                return  # not a top-up (e.g. a subscription invoice): nothing to claw back
            share = min(1.0, event.refunded_amount / event.total_amount)
            await credits.claw_back_purchased(s, row.user_id, round(row.delta * share), f"refund:{event.payment_ref}")

    async def _upsert_subscription(self, s: AsyncSession, user_id: int, ref: str, offer_id: Optional[str],
                                   status: str, period_end: Optional[datetime]) -> None:
        sub = await s.get(Subscription, user_id)
        now = datetime.now(timezone.utc)
        if sub is None:
            s.add(Subscription(user_id=user_id, provider=self.payments.name, external_ref=ref, offer_id=offer_id,
                               status=status, current_period_end=period_end, updated_at=now))
        else:
            sub.provider, sub.external_ref, sub.status, sub.updated_at = self.payments.name, ref, status, now
            sub.offer_id = offer_id or sub.offer_id
            sub.current_period_end = period_end or sub.current_period_end
        await s.flush()
