# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
"""Guard for user-supplied endpoint URLs (custom OpenAI-compatible BYOK endpoints).

The URL must be https, carry no credentials, and resolve only to public addresses. It is
checked when a key is saved *and* again before every request. Deployments should still block
private ranges at the network level (see docs/SAAS.md).
"""
import asyncio
import ipaddress
import socket
from typing import Callable, Optional
from urllib.parse import urlsplit


class UnsafeUrl(ValueError):
    pass


def _is_public(ip: ipaddress._BaseAddress) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


def _resolve(host: str, port: int) -> list[str]:
    infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return [i[4][0] for i in infos]


async def assert_public_https_url(url: str, resolver: Optional[Callable[[str, int], list[str]]] = None) -> str:
    """Return the normalised URL or raise UnsafeUrl."""
    parts = urlsplit(url.strip())
    if parts.scheme != "https":
        raise UnsafeUrl("Custom endpoints must use https")
    if parts.username or parts.password:
        raise UnsafeUrl("The URL must not contain credentials")
    host = parts.hostname
    if not host:
        raise UnsafeUrl("The URL has no host")
    try:
        port = parts.port or 443
    except ValueError as e:
        raise UnsafeUrl("Invalid port") from e

    try:
        addresses = [str(ipaddress.ip_address(host))]  # a literal IP
    except ValueError:
        if host.lower() == "localhost" or host.lower().endswith((".local", ".internal", ".localhost")):
            raise UnsafeUrl("Private host names are not allowed") from None
        try:
            addresses = await asyncio.to_thread(resolver or _resolve, host, port)
        except OSError as e:
            raise UnsafeUrl(f"Cannot resolve host '{host}'") from e
    if not addresses:
        raise UnsafeUrl(f"Cannot resolve host '{host}'")
    for address in addresses:
        if not _is_public(ipaddress.ip_address(address.split("%")[0])):
            raise UnsafeUrl("The endpoint resolves to a private or reserved address")
    return url.strip().rstrip("/")
