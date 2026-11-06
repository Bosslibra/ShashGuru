# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
"""Billing disabled: every operation reports that payments are unavailable."""
from typing import Mapping

from app.ports.payments import CheckoutRequest, ParsedWebhook, PaymentError


class NonePayments:
    name = "none"

    async def create_checkout(self, req: CheckoutRequest) -> str:
        raise PaymentError("Payments are not enabled on this deployment")

    async def create_portal(self, customer_ref: str, return_url: str) -> str:
        raise PaymentError("Payments are not enabled on this deployment")

    def parse_webhook(self, headers: Mapping[str, str], body: bytes) -> ParsedWebhook:
        raise PaymentError("Payments are not enabled on this deployment")

    async def cancel_subscription(self, subscription_ref: str) -> None:
        return None
