# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
"""Development-only auth: the token is literally ``dev:<subject>[:<email>]``. NEVER enable in production."""
from typing import Mapping

from app.ports.auth import AuthError, AuthEvent, Identity


class DevAuth:
    name = "dev"

    def __init__(self, admin_subjects: list[str] | None = None):
        self.admin_subjects = set(admin_subjects or [])

    async def verify_token(self, token: str) -> Identity:
        prefix, _, rest = token.partition(":")
        subject, _, email = rest.partition(":")
        if prefix != "dev" or not subject:
            raise AuthError("Dev tokens look like 'dev:<subject>[:<email>]'")
        return Identity(self.name, subject, email or None, subject in self.admin_subjects)

    def parse_webhook(self, headers: Mapping[str, str], body: bytes) -> list[AuthEvent]:
        return []

    async def delete_identity(self, subject: str) -> None:
        return None
