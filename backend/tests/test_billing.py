# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
"""Payment flows through the Stripe adapter with real signature verification and a fake API client."""
import hashlib
import hmac
import json
import time
from types import SimpleNamespace

import pytest

from app.adapters.payments.stripe import StripePayments
from app.ports.payments import CheckoutRequest, PaymentError, SubscriptionRenewed, TopupPaid
from app.services.billing.service import BillingService
from tests.conftest import bearer

SECRET = "whsec_test_secret"
A = bearer("alice")
PRO, SMALL = "price_REPLACE_ME_PRO_MONTHLY", "price_REPLACE_ME_TOPUP_SMALL"


class FakeStripeClient:
    def __init__(self):
        self.checkouts = []
        self.cancelled = []
        outer = self

        async def create_checkout(params):
            outer.checkouts.append(params)
            return SimpleNamespace(url="https://checkout.test/s/1")

        async def create_portal(params):
            return SimpleNamespace(url="https://portal.test/p/1")

        async def cancel(ref):
            outer.cancelled.append(ref)

        self.v1 = SimpleNamespace(
            checkout=SimpleNamespace(sessions=SimpleNamespace(create_async=lambda params: create_checkout(params))),
            billing_portal=SimpleNamespace(sessions=SimpleNamespace(create_async=lambda params: create_portal(params))),
            subscriptions=SimpleNamespace(cancel_async=cancel))


@pytest.fixture
async def shop(saas):
    stripe_client = FakeStripeClient()
    payments = StripePayments("sk_test", SECRET, saas.app.state.offers, client=stripe_client)
    billing = BillingService(saas.db, payments, saas.app.state.offers, "https://app.test")
    saas.app.state.payments, saas.app.state.billing = payments, billing
    saas.stripe = stripe_client
    saas.uid = (await saas.http.get("/api/v1/me", headers=A)).json()["id"]
    return saas


async def deliver(shop, event_type, obj, event_id=None, secret=SECRET):
    body = json.dumps({"id": event_id or f"evt_{time.time_ns()}", "type": event_type,
                       "data": {"object": obj}}).encode()
    ts = int(time.time())
    sig = hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    return await shop.http.post("/api/v1/webhooks/payments", content=body,
                                headers={"Stripe-Signature": f"t={ts},v1={sig}", "Content-Type": "application/json"})


def checkout_done(uid, mode, offer, customer="cus_1", pi="pi_1"):
    return {"mode": mode, "payment_status": "paid", "client_reference_id": str(uid), "customer": customer,
            "payment_intent": pi if mode == "payment" else None, "metadata": {"offer_id": offer, "user_id": str(uid)}}


def invoice(customer="cus_1", price=PRO, inv="in_1", sub="sub_1", end=2_000_000_000):
    return {"id": inv, "customer": customer, "subscription": sub,
            "lines": {"data": [{"price": {"id": price}, "period": {"end": end}}]}}


async def balance(shop):
    return (await shop.http.get("/api/v1/me", headers=A)).json()["balance"]


async def test_topup_credits_the_user_once_even_if_delivered_twice(shop):
    r = await deliver(shop, "checkout.session.completed", checkout_done(shop.uid, "payment", "topup_small"), "evt_a")
    assert r.json() == {"received": True, "duplicate": False}
    assert (await balance(shop))["purchased"] == 5000
    again = await deliver(shop, "checkout.session.completed", checkout_done(shop.uid, "payment", "topup_small"), "evt_a")
    assert again.json()["duplicate"] is True
    assert (await balance(shop))["purchased"] == 5000  # no double credit


async def test_subscription_lifecycle(shop):
    await deliver(shop, "checkout.session.completed", checkout_done(shop.uid, "subscription", "pro_monthly"))
    assert (await balance(shop))["subscription"] == 0  # credits arrive with the paid invoice, not the checkout
    await deliver(shop, "invoice.paid", invoice())
    me = (await shop.http.get("/api/v1/me", headers=A)).json()
    assert me["balance"]["subscription"] == 10000 and me["plan"] == "pro_monthly"
    assert me["subscription"]["status"] == "active" and me["subscription"]["current_period_end"].startswith("2033")

    # a premium model is now allowed, and the next period replaces what is left
    await deliver(shop, "invoice.paid", invoice(inv="in_2"))
    assert (await balance(shop))["subscription"] == 10000  # leftovers expire, they do not pile up

    await deliver(shop, "customer.subscription.deleted", {"id": "sub_1", "customer": "cus_1", "status": "canceled"})
    me = (await shop.http.get("/api/v1/me", headers=A)).json()
    assert me["plan"] is None and me["subscription"]["status"] == "canceled"


async def test_second_subscription_is_refused_while_one_is_active(shop):
    await deliver(shop, "checkout.session.completed", checkout_done(shop.uid, "subscription", "pro_monthly"))
    await deliver(shop, "invoice.paid", invoice())
    r = await shop.http.post("/api/v1/billing/checkout", json={"offer_id": "pro_monthly"}, headers=A)
    assert r.status_code == 409


async def test_refunds_claw_credits_back_proportionally(shop):
    await deliver(shop, "checkout.session.completed", checkout_done(shop.uid, "payment", "topup_small", pi="pi_9"))
    await deliver(shop, "charge.refunded", {"payment_intent": "pi_9", "amount": 500, "amount_refunded": 250})
    assert (await balance(shop))["purchased"] == 2500  # half refunded -> half of the credits removed
    await deliver(shop, "charge.refunded", {"payment_intent": "pi_other", "amount": 500, "amount_refunded": 500})
    assert (await balance(shop))["purchased"] == 2500  # unknown payment: ignored


async def test_bad_signature_is_rejected_and_changes_nothing(shop):
    r = await deliver(shop, "checkout.session.completed", checkout_done(shop.uid, "payment", "topup_small"),
                      secret="whsec_forged")
    assert r.status_code == 400
    assert (await balance(shop))["purchased"] == 0


async def test_events_for_unknown_prices_or_customers_are_harmless(shop):
    assert (await deliver(shop, "invoice.paid", invoice(price="price_unknown"))).status_code == 200
    assert (await deliver(shop, "invoice.paid", invoice(customer="cus_nobody"))).status_code == 200
    assert (await deliver(shop, "some.other.event", {})).status_code == 200
    assert (await balance(shop))["total"] == 0


async def test_checkout_and_portal_endpoints(shop):
    r = await shop.http.post("/api/v1/billing/checkout", json={"offer_id": "topup_small"}, headers=A)
    assert r.json() == {"url": "https://checkout.test/s/1"}
    params = shop.stripe.checkouts[0]
    assert params["mode"] == "payment" and params["line_items"] == [{"price": SMALL, "quantity": 1}]
    assert params["client_reference_id"] == str(shop.uid) and params["customer_email"] == "alice@example.com"
    assert params["success_url"].startswith("https://app.test/")  # never taken from the client
    assert (await shop.http.post("/api/v1/billing/checkout", json={"offer_id": "nope"}, headers=A)).status_code == 404
    assert (await shop.http.post("/api/v1/billing/portal", headers=A)).status_code == 404  # no customer yet
    await deliver(shop, "checkout.session.completed", checkout_done(shop.uid, "payment", "topup_small"))
    assert (await shop.http.post("/api/v1/billing/portal", headers=A)).json() == {"url": "https://portal.test/p/1"}
    await shop.http.post("/api/v1/billing/checkout", json={"offer_id": "topup_large"}, headers=A)
    assert shop.stripe.checkouts[-1]["customer"] == "cus_1"  # the known customer is reused


async def test_deleting_the_account_cancels_the_subscription(shop):
    await deliver(shop, "checkout.session.completed", checkout_done(shop.uid, "subscription", "pro_monthly"))
    await deliver(shop, "invoice.paid", invoice())
    assert (await shop.http.delete("/api/v1/me", headers=A)).status_code == 204
    assert shop.stripe.cancelled == ["sub_1"]


def test_adapter_normalises_newer_api_versions():
    """Stripe moved the subscription and price fields in newer API versions; both shapes are understood."""
    from app.services.billing.offers import Offers
    from app.config import DATA_DIR
    adapter = StripePayments("sk", SECRET, Offers.load(DATA_DIR / "offers.yaml"), client=object())
    new_style = {"id": "in_9", "customer": "cus_1",
                 "parent": {"subscription_details": {"subscription": "sub_9"}},
                 "lines": {"data": [{"pricing": {"price_details": {"price": PRO}}, "period": {"end": 1}}]}}
    (event,) = adapter._normalise("invoice.paid", new_style)
    assert isinstance(event, SubscriptionRenewed) and event.offer_id == "pro_monthly" and event.subscription_ref == "sub_9"
    topup = adapter._normalise("checkout.session.completed", checkout_done(7, "payment", "topup_small"))
    assert any(isinstance(e, TopupPaid) for e in topup)


async def test_payment_provider_none_rejects_everything(saas):
    assert (await saas.http.post("/api/v1/webhooks/payments", content=b"{}")).status_code == 400
    assert (await saas.http.post("/api/v1/billing/checkout", json={"offer_id": "pro_monthly"}, headers=A)).status_code == 400
    assert (await saas.http.get("/api/v1/offers")).json() == []
    assert (await saas.http.get("/api/v1/config")).json()["billing_enabled"] is False


async def test_checkout_request_is_provider_neutral():
    req = CheckoutRequest(1, None, "x", "topup", "price", None, "u", "c")
    assert not any("stripe" in f.lower() for f in req.__dataclass_fields__)
    with pytest.raises(PaymentError):
        StripePayments("sk", "", None, client=object()).parse_webhook({}, b"{}")
