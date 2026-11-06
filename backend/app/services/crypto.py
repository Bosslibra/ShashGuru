# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
"""Encryption at rest for users' API keys (AES-256-GCM, versioned keys for rotation)."""
import base64
import os
import secrets
from typing import Optional

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class CryptoError(Exception):
    pass


def generate_key() -> str:
    """A fresh master key, as accepted by KEY_ENCRYPTION_KEYS (``v1:<this>``)."""
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()


class KeyVault:
    """``spec`` is ``"v2:<b64>,v1:<b64>"``. The first entry encrypts; all of them decrypt."""

    def __init__(self, spec: str):
        self._keys: dict[str, bytes] = {}
        self._current: Optional[str] = None
        for part in filter(None, (p.strip() for p in spec.split(","))):
            version, _, raw = part.partition(":")
            if not version or not raw:
                raise CryptoError("KEY_ENCRYPTION_KEYS entries must look like 'v1:<base64 key>'")
            try:
                key = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
            except ValueError as e:  # binascii.Error
                raise CryptoError(f"Key {version} is not valid base64") from e
            if len(key) != 32:
                raise CryptoError(f"Key {version} must be 32 bytes (use `generate_key()`)")
            self._keys[version] = key
            self._current = self._current or version

    @property
    def configured(self) -> bool:
        return self._current is not None

    def encrypt(self, plaintext: str, aad: bytes = b"") -> tuple[bytes, bytes, str]:
        if not self._current:
            raise CryptoError("No encryption key configured (KEY_ENCRYPTION_KEYS)")
        nonce = os.urandom(12)
        ciphertext = AESGCM(self._keys[self._current]).encrypt(nonce, plaintext.encode(), aad)
        return ciphertext, nonce, self._current

    def decrypt(self, ciphertext: bytes, nonce: bytes, version: str, aad: bytes = b"") -> str:
        key = self._keys.get(version)
        if key is None:
            raise CryptoError(f"Unknown key version '{version}'")
        try:
            return AESGCM(key).decrypt(nonce, ciphertext, aad).decode()
        except InvalidTag as e:
            raise CryptoError("Stored key could not be decrypted") from e
