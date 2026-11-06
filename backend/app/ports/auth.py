# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
"""Authentication port.

The application depends only on these types. Vendor specifics (Clerk, Auth0, ...) live in
``app.adapters.auth`` and nothing outside that package may import a vendor SDK.
"""
from dataclasses import dataclass
from typing import Mapping, Optional, Protocol, Union


class AuthError(Exception):
    """The credentials are missing, malformed, expired or otherwise invalid."""


@dataclass(frozen=True)
class Identity:
    """Who the caller is, as asserted by the auth provider."""
    provider: str
    subject: str
    email: Optional[str] = None
    is_admin: bool = False


@dataclass(frozen=True)
class UserDeleted:
    provider: str
    subject: str


@dataclass(frozen=True)
class UserUpdated:
    provider: str
    subject: str
    email: Optional[str] = None


AuthEvent = Union[UserDeleted, UserUpdated]


class AuthProvider(Protocol):
    name: str

    async def verify_token(self, token: str) -> Identity:
        """Validate a bearer token. Raises AuthError."""

    def parse_webhook(self, headers: Mapping[str, str], body: bytes) -> list[AuthEvent]:
        """Verify and normalise a provider webhook. Raises AuthError on a bad signature."""

    async def delete_identity(self, subject: str) -> None:
        """Best effort: remove the identity at the provider when the user erases their account."""
