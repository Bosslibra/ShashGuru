# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
"""Provider-neutral schema: no column is named after Clerk, Stripe or any other vendor."""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, LargeBinary, String,
                        UniqueConstraint)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("auth_provider", "auth_subject", name="uq_users_auth"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    auth_provider: Mapped[str] = mapped_column(String(32))
    auth_subject: Mapped[str] = mapped_column(String(255))
    email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class ExternalRef(Base):
    """Maps one of our users to an id in an external system (e.g. a payment provider customer)."""
    __tablename__ = "external_refs"
    __table_args__ = (UniqueConstraint("provider", "kind", "ref", name="uq_external_ref"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(32))
    kind: Mapped[str] = mapped_column(String(32))  # "customer" | "subscription"
    ref: Mapped[str] = mapped_column(String(255))


class ProviderKey(Base):
    """A user's own LLM API key (BYOK), stored encrypted."""
    __tablename__ = "provider_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(32))  # openai | anthropic | openrouter | custom
    base_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
    nonce: Mapped[bytes] = mapped_column(LargeBinary)
    key_version: Mapped[str] = mapped_column(String(16))
    hint: Mapped[str] = mapped_column(String(8))
    label: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class Subscription(Base):
    __tablename__ = "subscriptions"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    provider: Mapped[str] = mapped_column(String(32))
    external_ref: Mapped[str] = mapped_column(String(255))
    offer_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32))
    current_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CreditBalance(Base):
    """Materialised balance. Updated with optimistic locking (``version``) together with the ledger."""
    __tablename__ = "credit_balances"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    subscription_credits: Mapped[int] = mapped_column(BigInteger, default=0)
    purchased_credits: Mapped[int] = mapped_column(BigInteger, default=0)
    version: Mapped[int] = mapped_column(Integer, default=0)


class CreditLedger(Base):
    __tablename__ = "credit_ledger"
    __table_args__ = (Index("ix_ledger_ref", "reason", "ref"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    bucket: Mapped[str] = mapped_column(String(16))  # subscription | purchased
    delta: Mapped[int] = mapped_column(BigInteger)
    reason: Mapped[str] = mapped_column(String(16))  # grant|topup|hold|release|expire|refund|adjust
    ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    analysis_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    source: Mapped[str] = mapped_column(String(16))  # managed | byok
    provider: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(128))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    hold_subscription: Mapped[int] = mapped_column(BigInteger, default=0)
    hold_purchased: Mapped[int] = mapped_column(BigInteger, default=0)
    credits_charged: Mapped[int] = mapped_column(BigInteger, default=0)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending | ok | error | aborted
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class WebhookEvent(Base):
    """Idempotency log of processed provider webhooks (payments and auth)."""
    __tablename__ = "webhook_events"

    provider: Mapped[str] = mapped_column(String(32), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
