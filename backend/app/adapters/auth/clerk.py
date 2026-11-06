# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
"""Clerk: OIDC token verification (inherited) plus Clerk's Svix-signed lifecycle webhooks."""
import base64
import hashlib
import hmac
import json
import logging
import time
from typing import Mapping

import httpx

from app.adapters.auth.oidc import OidcAuth
from app.ports.auth import AuthError, AuthEvent, UserDeleted, UserUpdated

log = logging.getLogger(__name__)
TOLERANCE_SECONDS = 300


def _verify_svix(secret: str, headers: Mapping[str, str], body: bytes, now: float | None = None) -> None:
    h = {k.lower(): v for k, v in headers.items()}
    try:
        msg_id, ts, signatures = h["svix-id"], h["svix-timestamp"], h["svix-signature"]
        key = base64.b64decode(secret.removeprefix("whsec_"))
        ts_int = int(ts)
    except (KeyError, ValueError) as e:
        raise AuthError("Missing or malformed webhook headers") from e
    if abs((now if now is not None else time.time()) - ts_int) > TOLERANCE_SECONDS:
        raise AuthError("Webhook timestamp outside tolerance")
    expected = base64.b64encode(hmac.new(key, f"{msg_id}.{ts}.".encode() + body, hashlib.sha256).digest()).decode()
    for candidate in signatures.split():
        _, _, sig = candidate.partition(",")
        if hmac.compare_digest(sig, expected):
            return
    raise AuthError("Invalid webhook signature")


class ClerkAuth(OidcAuth):
    name = "clerk"

    def __init__(self, *, webhook_secret: str = "", secret_key: str = "", **kwargs):
        kwargs.setdefault("provider_name", "clerk")
        super().__init__(**kwargs)
        self._webhook_secret = webhook_secret
        self._secret_key = secret_key

    async def delete_identity(self, subject: str) -> None:
        """Erase the user in Clerk too (GDPR). Needs AUTH_SECRET_KEY; without it only our data is erased."""
        if not self._secret_key:
            log.warning("AUTH_SECRET_KEY not set: Clerk user %s was not deleted at the provider", subject)
            return
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.delete(f"https://api.clerk.com/v1/users/{subject}",
                                           headers={"Authorization": f"Bearer {self._secret_key}"})
        if response.status_code not in (200, 404):
            raise AuthError(f"Clerk refused to delete the user ({response.status_code})")

    def parse_webhook(self, headers: Mapping[str, str], body: bytes) -> list[AuthEvent]:
        if not self._webhook_secret:
            raise AuthError("Clerk webhook secret is not configured")
        _verify_svix(self._webhook_secret, headers, body)
        try:
            payload = json.loads(body)
            kind, data = payload["type"], payload["data"]
        except (ValueError, KeyError) as e:
            raise AuthError("Malformed webhook payload") from e
        subject = data.get("id")
        if not subject:
            return []
        if kind == "user.deleted":
            return [UserDeleted(self.name, subject)]
        if kind in ("user.created", "user.updated"):
            primary = data.get("primary_email_address_id")
            emails = data.get("email_addresses") or []
            chosen = next((e for e in emails if e.get("id") == primary), emails[0] if emails else None)
            return [UserUpdated(self.name, subject, (chosen or {}).get("email_address"))]
        return []
