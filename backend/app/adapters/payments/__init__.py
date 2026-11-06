# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
"""Payment adapters. To support another provider add a module here and a branch in `build_payments`."""
from app.config import Settings
from app.ports.payments import PaymentProvider
from app.services.billing.offers import Offers


def build_payments(settings: Settings, offers: Offers) -> PaymentProvider:
    if settings.payment_provider == "stripe":
        from app.adapters.payments.stripe import StripePayments
        if not settings.stripe_secret_key:
            raise RuntimeError("PAYMENT_PROVIDER=stripe requires STRIPE_SECRET_KEY")
        return StripePayments(settings.stripe_secret_key, settings.stripe_webhook_secret, offers,
                              automatic_tax=settings.stripe_automatic_tax)
    from app.adapters.payments.none import NonePayments
    return NonePayments()
