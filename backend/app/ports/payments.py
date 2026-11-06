# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
"""Payments port.

The domain (credits, subscriptions) speaks only in terms of these normalised events and of
offers (see services.billing.offers). Provider ids are opaque ``*_ref`` strings.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Optional, Protocol, Union


class PaymentError(Exception):
    """Provider call failed or a webhook did not verify."""


@dataclass(frozen=True)
class CheckoutRequest:
    user_id: int
    email: Optional[str]
    offer_id: str
    kind: str  # "subscription" | "topup"
    external_price_id: str  # the offer's id at this provider
    customer_ref: Optional[str]
    success_url: str
    cancel_url: str


# ---- normalised events (provider -> domain) ---------------------------------

@dataclass(frozen=True)
class CustomerLinked:
    """The provider customer `customer_ref` belongs to our user `user_id`."""
    user_id: int
    customer_ref: str


@dataclass(frozen=True)
class TopupPaid:
    offer_id: str
    payment_ref: str
    user_id: Optional[int] = None
    customer_ref: Optional[str] = None


@dataclass(frozen=True)
class SubscriptionRenewed:
    """A subscription period was paid: grant the offer's monthly credits."""
    offer_id: str
    customer_ref: str
    subscription_ref: str
    invoice_ref: str
    period_end: Optional[datetime] = None


@dataclass(frozen=True)
class SubscriptionChanged:
    offer_id: Optional[str]
    customer_ref: str
    subscription_ref: str
    status: str  # active | past_due | canceled | ...
    period_end: Optional[datetime] = None


@dataclass(frozen=True)
class Refunded:
    payment_ref: str
    refunded_amount: int
    total_amount: int


BillingEvent = Union[CustomerLinked, TopupPaid, SubscriptionRenewed, SubscriptionChanged, Refunded]


@dataclass(frozen=True)
class ParsedWebhook:
    event_id: str  # unique per delivery, used for idempotency
    events: list[BillingEvent]


class PaymentProvider(Protocol):
    name: str

    async def create_checkout(self, req: CheckoutRequest) -> str:
        """Return the URL the browser must be redirected to."""

    async def create_portal(self, customer_ref: str, return_url: str) -> str:
        """Return the URL of the customer self-service portal."""

    def parse_webhook(self, headers: Mapping[str, str], body: bytes) -> ParsedWebhook:
        """Verify the signature and normalise the payload. Raises PaymentError."""

    async def cancel_subscription(self, subscription_ref: str) -> None:
        """Cancel immediately (used when an account is deleted)."""
