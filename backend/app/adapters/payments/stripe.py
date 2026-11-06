# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
"""Stripe adapter. The only module that imports ``stripe`` (enforced by tests/test_architecture.py)."""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

import stripe

from app.ports.payments import (BillingEvent, CheckoutRequest, CustomerLinked, ParsedWebhook, PaymentError, Refunded,
                                SubscriptionChanged, SubscriptionRenewed, TopupPaid)
from app.services.billing.offers import Offers

log = logging.getLogger(__name__)
PROVIDER = "stripe"


def _dig(obj: Any, *path: str) -> Any:
    for key in path:
        if isinstance(obj, list):
            try:
                obj = obj[int(key)]
            except (ValueError, IndexError):
                return None
        elif isinstance(obj, dict):
            obj = obj.get(key)
        else:
            return None
        if obj is None:
            return None
    return obj


def _first(obj: Any, *paths: tuple[str, ...]) -> Any:
    """The first non-empty value among several paths (Stripe moved some fields between API versions)."""
    for path in paths:
        value = _dig(obj, *path)
        if value:
            return value
    return None


def _ts(value: Any) -> Optional[datetime]:
    return datetime.fromtimestamp(int(value), tz=timezone.utc) if value else None


def _int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class StripePayments:
    name = PROVIDER

    def __init__(self, secret_key: str, webhook_secret: str, offers: Offers, *, automatic_tax: bool = False,
                 client: Any = None):
        self._client = client or stripe.StripeClient(secret_key)
        self._webhook_secret = webhook_secret
        self._offers = offers
        self._automatic_tax = automatic_tax

    # ---- outbound -----------------------------------------------------------------------------

    async def create_checkout(self, req: CheckoutRequest) -> str:
        meta = {"user_id": str(req.user_id), "offer_id": req.offer_id}
        params: dict[str, Any] = {
            "mode": "subscription" if req.kind == "subscription" else "payment",
            "line_items": [{"price": req.external_price_id, "quantity": 1}],
            "success_url": req.success_url,
            "cancel_url": req.cancel_url,
            "client_reference_id": str(req.user_id),
            "metadata": meta,
            "allow_promotion_codes": True,
        }
        if self._automatic_tax:
            params["automatic_tax"] = {"enabled": True}
        if req.kind == "subscription":
            params["subscription_data"] = {"metadata": meta}
        else:
            params["payment_intent_data"] = {"metadata": meta}
        if req.customer_ref:
            params["customer"] = req.customer_ref
        else:
            if req.kind != "subscription":
                params["customer_creation"] = "always"
            if req.email:
                params["customer_email"] = req.email
        try:
            session = await self._client.v1.checkout.sessions.create_async(params=params)
        except stripe.StripeError as e:
            raise PaymentError(f"Stripe checkout failed: {e}") from e
        return session.url

    async def create_portal(self, customer_ref: str, return_url: str) -> str:
        try:
            session = await self._client.v1.billing_portal.sessions.create_async(
                params={"customer": customer_ref, "return_url": return_url})
        except stripe.StripeError as e:
            raise PaymentError(f"Stripe portal failed: {e}") from e
        return session.url

    async def cancel_subscription(self, subscription_ref: str) -> None:
        try:
            await self._client.v1.subscriptions.cancel_async(subscription_ref)
        except stripe.StripeError as e:
            raise PaymentError(f"Stripe cancel failed: {e}") from e

    # ---- inbound ------------------------------------------------------------------------------

    def parse_webhook(self, headers: Mapping[str, str], body: bytes) -> ParsedWebhook:
        h = {k.lower(): v for k, v in headers.items()}
        if not self._webhook_secret:
            raise PaymentError("Stripe webhook secret is not configured")
        try:
            stripe.Webhook.construct_event(body, h.get("stripe-signature"), self._webhook_secret)
            event = json.loads(body)  # verified: work on plain dicts from here on
        except (stripe.SignatureVerificationError, ValueError) as e:
            raise PaymentError(f"Invalid webhook: {e}") from e
        return ParsedWebhook(event_id=event["id"], events=self._normalise(event["type"], event["data"]["object"]))

    def _offer_id(self, price_id: Optional[str]) -> Optional[str]:
        offer = self._offers.by_external(PROVIDER, price_id) if price_id else None
        return offer.id if offer else None

    def _normalise(self, kind: str, obj: dict) -> list[BillingEvent]:
        events: list[BillingEvent] = []

        if kind in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
            user_id = _int(obj.get("client_reference_id") or _dig(obj, "metadata", "user_id"))
            customer = obj.get("customer")
            if user_id and customer:
                events.append(CustomerLinked(user_id, customer))
            if obj.get("mode") == "payment" and obj.get("payment_status") == "paid":
                offer_id = _dig(obj, "metadata", "offer_id")
                if offer_id and obj.get("payment_intent"):
                    events.append(TopupPaid(offer_id, obj["payment_intent"], user_id, customer))

        elif kind == "invoice.paid":
            sub = _first(obj, ("subscription",), ("parent", "subscription_details", "subscription"))
            if sub:
                price = _first(obj, ("lines", "data", "0", "price", "id"),
                               ("lines", "data", "0", "pricing", "price_details", "price"))
                offer_id = self._offer_id(price)
                if offer_id and obj.get("customer"):
                    events.append(SubscriptionRenewed(
                        offer_id, obj["customer"], sub, obj["id"],
                        _ts(_dig(obj, "lines", "data", "0", "period", "end"))))
                else:
                    log.warning("invoice.paid for an unknown price %s, ignored", price)

        elif kind in ("customer.subscription.created", "customer.subscription.updated",
                      "customer.subscription.deleted"):
            status = "canceled" if kind.endswith("deleted") else obj.get("status", "")
            status = "active" if status == "trialing" else status
            events.append(SubscriptionChanged(
                self._offer_id(_dig(obj, "items", "data", "0", "price", "id")), obj.get("customer", ""),
                obj["id"], status,
                _ts(_first(obj, ("current_period_end",), ("items", "data", "0", "current_period_end")))))

        elif kind == "charge.refunded":
            if obj.get("payment_intent"):
                events.append(Refunded(obj["payment_intent"], int(obj.get("amount_refunded") or 0),
                                       int(obj.get("amount") or 0)))
        return events
