# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
"""No authentication (self-hosted). Every caller is the local administrator."""
from typing import Mapping

from app.ports.auth import AuthError, AuthEvent, Identity


class NoneAuth:
    name = "none"

    async def verify_token(self, token: str) -> Identity:
        raise AuthError("Authentication is disabled on this deployment")

    def parse_webhook(self, headers: Mapping[str, str], body: bytes) -> list[AuthEvent]:
        return []

    async def delete_identity(self, subject: str) -> None:
        return None
