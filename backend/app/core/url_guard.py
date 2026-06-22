"""SSRF protection for outbound HTTP from agent tools.

LLM-driven tools (web scraper, scout, gemini_search) can be coerced — via
prompt injection in scraped content, untrusted user input, or a cleverly
crafted research objective — into making requests to internal endpoints
such as AWS/GCP IMDS (``169.254.169.254``), loopback services, or RFC-1918
network resources. These endpoints are not behind any application-level
authentication and frequently return credentials.

This module rejects:
- Non ``http``/``https`` schemes (``file://``, ``ftp://``, ``gopher://`` etc.)
- Hostnames that resolve to loopback (``127.0.0.0/8``, ``::1``)
- Link-local (``169.254.0.0/16``, ``fe80::/10`` — covers cloud IMDS)
- Private RFC-1918 (``10.0.0.0/8``, ``172.16.0.0/12``, ``192.168.0.0/16``)
- Unique-local IPv6 (``fc00::/7``)
- Multicast / unspecified / reserved ranges
- Hostnames that fail to resolve (avoids using DNS as an oracle)

Redirect-time enforcement
-------------------------
``safe_http_get`` follows up to ``max_redirects`` hops, re-validating the
target URL on each redirect. This is required because a benign-looking
hostname can redirect to ``169.254.169.254`` once contacted — disabling
auto-follow and validating each Location header closes the gap.
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from typing import Final
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

ALLOWED_SCHEMES: Final[frozenset[str]] = frozenset({"http", "https"})
DEFAULT_MAX_REDIRECTS: Final[int] = 5


class UnsafeURLError(ValueError):
    """The URL targets an address space we will not request from."""


def _is_unsafe_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> str | None:
    """Return a reason string if the IP is in a blocked range, else None."""
    if ip.is_loopback:
        return "loopback address"
    if ip.is_link_local:
        return "link-local address (cloud IMDS)"
    if ip.is_private:
        return "private RFC-1918 address"
    if ip.is_multicast:
        return "multicast address"
    if ip.is_reserved:
        return "reserved address"
    if ip.is_unspecified:
        return "unspecified address"
    # IPv6 unique-local (fc00::/7) is covered by is_private in stdlib >=3.4
    return None


def _resolve_all_addrs(host: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    """Resolve a hostname to every address it advertises.

    We check *all* records because an attacker can return one safe and one
    unsafe record and exploit which one the HTTP client picks.
    """
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"DNS resolution failed for {host}: {exc}") from exc

    addrs: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for info in infos:
        sockaddr = info[4]
        try:
            addrs.append(ipaddress.ip_address(sockaddr[0]))
        except ValueError:
            continue
    return addrs


def assert_safe_url(url: str) -> None:
    """Validate that a URL is safe to fetch.

    Raises ``UnsafeURLError`` if the URL is malformed, uses a forbidden
    scheme, or resolves to a blocked address. Otherwise returns None.
    """
    parsed = urlparse(url)

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise UnsafeURLError(f"Scheme {parsed.scheme!r} is not allowed; only http/https permitted")

    host = parsed.hostname
    if not host:
        raise UnsafeURLError("URL is missing a hostname")

    # Reject literal IPs that fall in blocked ranges before DNS round-trip
    try:
        literal_ip = ipaddress.ip_address(host)
    except ValueError:
        literal_ip = None

    if literal_ip is not None:
        reason = _is_unsafe_ip(literal_ip)
        if reason:
            raise UnsafeURLError(f"{host} is {reason}")
        return

    # Hostname — resolve and reject if *any* record is unsafe
    addrs = _resolve_all_addrs(host)
    if not addrs:
        raise UnsafeURLError(f"{host} did not resolve to any addresses")

    for addr in addrs:
        reason = _is_unsafe_ip(addr)
        if reason:
            raise UnsafeURLError(f"{host} resolves to {reason} ({addr})")


async def safe_http_get(
    url: str,
    *,
    client: httpx.AsyncClient | None = None,
    max_redirects: int = DEFAULT_MAX_REDIRECTS,
    **request_kwargs,
) -> httpx.Response:
    """Perform an HTTP GET that revalidates every redirect target.

    The client must be created with ``follow_redirects=False`` (we follow
    manually so each hop is re-validated). If no client is supplied a
    transient one is created with the default timeout.

    Raises ``UnsafeURLError`` if any hop targets a blocked address. Raises
    ``httpx.TooManyRedirects`` if the redirect chain exceeds the cap.
    """
    owned_client = client is None
    if owned_client:
        client = httpx.AsyncClient(timeout=20, follow_redirects=False)

    try:
        current_url = url
        for _ in range(max_redirects + 1):
            assert_safe_url(current_url)
            response = await client.get(current_url, **request_kwargs)
            if response.is_redirect:
                location = response.headers.get("location", "")
                if not location:
                    return response
                # Resolve relative redirects against the current URL
                current_url = str(httpx.URL(current_url).join(location))
                continue
            return response
        raise httpx.TooManyRedirects(
            f"Exceeded {max_redirects} redirects starting from {url}",
            request=httpx.Request("GET", url),
        )
    finally:
        if owned_client:
            await client.aclose()
