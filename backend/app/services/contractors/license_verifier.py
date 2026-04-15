"""License verification for pool contractors.

Stream C v1 supports Texas only (TDLR public search). Other states
return ``LicenseStatus(found=False, status="state_not_supported")`` via
the ``verify_license`` dispatcher.

Network calls are wrapped in a 24h Redis cache that degrades gracefully
when Redis is unavailable.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import asdict, dataclass
from typing import Any

import httpx
from bs4 import BeautifulSoup

from ...config import settings

logger = logging.getLogger(__name__)

_TDLR_URL = "https://www.tdlr.texas.gov/LicenseSearch/"
_HTTP_TIMEOUT = 10.0
_CACHE_TTL_SECONDS = 24 * 60 * 60  # 24h
_CACHE_KEY_PREFIX = "contractor_license:"


@dataclass(frozen=True)
class LicenseStatus:
    """Outcome of a license-search lookup."""

    found: bool
    license_number: str | None = None
    status: str | None = None
    classification: str | None = None
    expires_at: str | None = None  # ISO-8601 if parseable, raw text otherwise
    source: str = "tdlr"
    raw_html_len: int = 0


# ---------------------------------------------------------------------------
# Redis cache (lazy, resilient)
# ---------------------------------------------------------------------------

_redis_client: Any | None = None
# Audit fix (code-review HIGH #8): previously ``_redis_unavailable``
# latched True on the first failure and never retried for the life of
# the process. A 60-second monotonic backoff lets the verifier recover
# once Redis comes back.
_redis_retry_after: float = 0.0
_REDIS_RETRY_BACKOFF_SECONDS: float = 60.0


async def _get_redis() -> Any | None:
    """Return a shared ``aioredis`` client or ``None`` if Redis is down.

    When a connection attempt fails we mark ``_redis_retry_after`` to
    ``monotonic() + 60s`` and short-circuit further calls until that
    window elapses. After the window we attempt to reconnect.
    """
    global _redis_client, _redis_retry_after
    if _redis_client is not None:
        return _redis_client
    if time.monotonic() < _redis_retry_after:
        return None
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(
            settings.redis_url, decode_responses=True
        )
        await client.ping()
        _redis_client = client
        _redis_retry_after = 0.0
        return client
    except Exception as exc:  # pragma: no cover — infra edge case
        logger.warning("License verifier: Redis unavailable (%s)", exc)
        _redis_retry_after = time.monotonic() + _REDIS_RETRY_BACKOFF_SECONDS
        return None


def _cache_key(state: str, business_name: str, city: str | None) -> str:
    raw = json.dumps(
        {
            "state": state.upper().strip(),
            "name": business_name.lower().strip(),
            "city": (city or "").lower().strip(),
        },
        sort_keys=True,
    )
    digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"{_CACHE_KEY_PREFIX}{digest}"


async def _cache_get(key: str) -> LicenseStatus | None:
    client = await _get_redis()
    if client is None:
        return None
    try:
        payload = await client.get(key)
        if not payload:
            return None
        data = json.loads(payload)
        return LicenseStatus(**data)
    except Exception as exc:  # pragma: no cover
        logger.debug("License cache get failed: %s", exc)
        return None


async def _cache_set(key: str, value: LicenseStatus) -> None:
    client = await _get_redis()
    if client is None:
        return
    try:
        await client.setex(
            key, _CACHE_TTL_SECONDS, json.dumps(asdict(value))
        )
    except Exception as exc:  # pragma: no cover
        logger.debug("License cache set failed: %s", exc)


# ---------------------------------------------------------------------------
# TDLR parser
# ---------------------------------------------------------------------------


def _parse_tdlr_html(html: str) -> LicenseStatus:
    """Parse the HTML body returned by the TDLR public license search.

    The public search page renders a ``<table>`` of matches. We look for
    the first row and extract license number, status, classification,
    and expiry. When the page says "No records found" or the table is
    missing we return ``found=False``.
    """
    if not html:
        return LicenseStatus(found=False, status="empty_response")

    lowered = html.lower()
    if "no records found" in lowered or "no results" in lowered:
        return LicenseStatus(
            found=False, status="no_records", raw_html_len=len(html)
        )

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if table is None:
        return LicenseStatus(
            found=False, status="no_table", raw_html_len=len(html)
        )

    rows = table.find_all("tr")
    # Pull header cells to make column lookups resilient to reorder.
    header_cells = rows[0].find_all(["th", "td"]) if rows else []
    headers = [c.get_text(strip=True).lower() for c in header_cells]

    def _col(cols: list[str], *needles: str) -> str | None:
        for needle in needles:
            for idx, header in enumerate(headers):
                if needle in header and idx < len(cols):
                    value = cols[idx].strip()
                    if value:
                        return value
        return None

    for row in rows[1:]:
        cells = row.find_all(["td", "th"])
        cols = [c.get_text(strip=True) for c in cells]
        if not cols or all(not c for c in cols):
            continue
        license_number = _col(cols, "license")
        status = _col(cols, "status")
        classification = _col(cols, "type", "classification", "category")
        expires_at = _col(cols, "expir")
        if license_number or status:
            return LicenseStatus(
                found=True,
                license_number=license_number,
                status=status,
                classification=classification,
                expires_at=expires_at,
                raw_html_len=len(html),
            )

    return LicenseStatus(
        found=False, status="no_rows", raw_html_len=len(html)
    )


async def _fetch_tdlr(business_name: str, city: str | None) -> str:
    """Fetch the TDLR public search page for a business name.

    Audit fix (security #7): explicitly disable redirect-following so a
    hostile redirect (or a state-side TDLR outage that bounces us to an
    unexpected host) cannot cause us to execute a cross-origin request
    carrying our query parameters. 3xx responses surface as HTTP errors
    via the caller's existing handling.
    """
    params: dict[str, str] = {"CompanyName": business_name}
    if city:
        params["City"] = city
    async with httpx.AsyncClient(
        timeout=_HTTP_TIMEOUT, follow_redirects=False
    ) as client:
        response = await client.get(_TDLR_URL, params=params)
        response.raise_for_status()
        return response.text


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def verify_tx_license(
    business_name: str,
    city: str | None = None,
) -> LicenseStatus:
    """Look up a business in TX TDLR, with 24h Redis cache.

    Returns ``found=False`` (rather than raising) on timeouts, HTTP
    errors, or empty results — callers treat missing licenses as
    "unverified" and skip the contractor.
    """
    if not business_name or not business_name.strip():
        return LicenseStatus(found=False, status="no_business_name")

    key = _cache_key("TX", business_name, city)
    cached = await _cache_get(key)
    if cached is not None:
        return cached

    try:
        html = await _fetch_tdlr(business_name.strip(), city)
    except (httpx.TimeoutException, asyncio.TimeoutError):
        logger.warning(
            "TDLR timeout for business=%r city=%r", business_name, city
        )
        return LicenseStatus(found=False, status="timeout")
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "TDLR HTTP %s for business=%r",
            exc.response.status_code,
            business_name,
        )
        return LicenseStatus(
            found=False, status=f"http_{exc.response.status_code}"
        )
    except Exception as exc:  # pragma: no cover — network edge cases
        logger.warning("TDLR request failed: %s", exc)
        return LicenseStatus(found=False, status="request_failed")

    status = _parse_tdlr_html(html)
    await _cache_set(key, status)
    return status


async def verify_license(
    state: str,
    business_name: str,
    city: str | None = None,
) -> LicenseStatus:
    """Dispatch license verification by state.

    Currently only TX is wired. Other states return
    ``LicenseStatus(found=False, status="state_not_supported")``.
    """
    normalized = (state or "").strip().upper()
    if normalized == "TX":
        return await verify_tx_license(business_name=business_name, city=city)
    return LicenseStatus(
        found=False, status="state_not_supported", source=normalized or "unknown"
    )
