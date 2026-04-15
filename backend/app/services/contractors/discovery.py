"""Discover in-ground pool contractors near a given ZIP.

Calls Yelp Fusion and Google Places (New) in parallel, merges and
deduplicates by a normalized ``(phone, name)`` key, filters by minimum
rating and review count, and ranks by ``rating * log(reviews + 1)``.

The connectors are constructed lazily so this module does not crash at
import time when API keys are absent — discovery simply returns an empty
list (or whatever the mock layer of each connector supplies) in that
case.
"""
from __future__ import annotations

import asyncio
import logging
import math
import re
from dataclasses import dataclass
from typing import Any, Literal

from ...config import settings
from ..data_sources.connectors.google_places import GooglePlacesConnector
from ..data_sources.connectors.yelp import YelpConnector

logger = logging.getLogger(__name__)

_CONTRACTOR_QUERY = "in-ground pool installer"
_MILES_TO_METERS = 1609.34
# Yelp caps radius at 40 km per docs — mirror the check in
# ``YelpConnector`` without relying on implementation details.
_YELP_MAX_METERS = 40_000

ContractorSource = Literal["yelp", "google_places"]


@dataclass(frozen=True)
class ContractorCandidate:
    """Single contractor discovered via Yelp or Google Places."""

    name: str
    phone: str
    address: str
    rating: float
    reviews_count: int
    source: ContractorSource
    business_url: str
    raw_payload: dict[str, Any]


def _normalize_phone(phone: str | None) -> str:
    """Reduce a phone number to digits for stable deduplication.

    Strips punctuation and, for US numbers, the leading ``1`` country
    code so ``+1-214-555-0101`` and ``(214) 555-0101`` dedupe together.
    """
    if not phone:
        return ""
    digits = re.sub(r"\D+", "", phone)
    if len(digits) == 11 and digits.startswith("1"):
        return digits[1:]
    return digits


def _normalize_name(name: str | None) -> str:
    """Lowercase and strip whitespace/punctuation for stable de-duping."""
    if not name:
        return ""
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def _dedup_key(name: str, phone: str) -> str:
    """Stable key for deduplicating discovery hits.

    Phone takes priority when present; otherwise fall back to name.
    """
    digits = _normalize_phone(phone)
    if digits:
        return f"p:{digits}"
    return f"n:{_normalize_name(name)}"


def _rank_score(rating: float, reviews: int) -> float:
    """Discovery ranking weight: rating * log(reviews + 1)."""
    return float(rating) * math.log(max(int(reviews), 0) + 1)


def _from_yelp(raw: dict[str, Any]) -> ContractorCandidate | None:
    """Convert a Yelp search result into a :class:`ContractorCandidate`."""
    rating = raw.get("rating")
    reviews = raw.get("review_count")
    phone = raw.get("phone") or ""
    name = raw.get("name") or ""
    if rating is None or reviews is None or not name:
        return None
    return ContractorCandidate(
        name=name,
        phone=phone,
        address=raw.get("address", "") or "",
        rating=float(rating),
        reviews_count=int(reviews),
        source="yelp",
        business_url=raw.get("url", "") or "",
        raw_payload=raw,
    )


def _from_google(raw: dict[str, Any]) -> ContractorCandidate | None:
    """Convert a Google Places result into a :class:`ContractorCandidate`."""
    rating = raw.get("rating")
    reviews = raw.get("total_ratings")
    name = raw.get("name") or ""
    if rating is None or reviews is None or not name:
        return None
    return ContractorCandidate(
        name=name,
        phone=raw.get("phone", "") or "",
        address=raw.get("address", "") or "",
        rating=float(rating),
        reviews_count=int(reviews),
        source="google_places",
        business_url=raw.get("website", "") or "",
        raw_payload=raw,
    )


async def _search_yelp(
    zipcode: str, radius_m: int, limit: int
) -> list[ContractorCandidate]:
    """Search Yelp for pool contractors near ``zipcode``."""
    if not settings.yelp_api_key:
        logger.info("Yelp API key missing — skipping Yelp discovery")
        return []
    try:
        connector = YelpConnector(api_key=settings.yelp_api_key)
        result = await connector.search(
            query=zipcode,
            term=_CONTRACTOR_QUERY,
            location=zipcode,
            radius=min(radius_m, _YELP_MAX_METERS),
            sort_by="rating",
        )
    except Exception:  # pragma: no cover — network edge cases
        logger.exception("Yelp discovery failed for zip=%s", zipcode)
        return []
    hits = [_from_yelp(r) for r in result.data[:limit]]
    return [c for c in hits if c is not None]


async def _search_google(
    zipcode: str, radius_m: int, limit: int
) -> list[ContractorCandidate]:
    """Search Google Places for pool contractors near ``zipcode``."""
    try:
        connector = GooglePlacesConnector()
        result = await connector.search(
            query=f"{_CONTRACTOR_QUERY} near {zipcode}",
            radius_meters=radius_m,
        )
    except Exception:  # pragma: no cover — network edge cases
        logger.exception("Google Places discovery failed for zip=%s", zipcode)
        return []
    hits = [_from_google(r) for r in result.data[:limit]]
    return [c for c in hits if c is not None]


def _dedup(
    candidates: list[ContractorCandidate],
) -> list[ContractorCandidate]:
    """Merge duplicates, keeping the higher review_count entry."""
    by_key: dict[str, ContractorCandidate] = {}
    for cand in candidates:
        key = _dedup_key(cand.name, cand.phone)
        existing = by_key.get(key)
        if existing is None or cand.reviews_count > existing.reviews_count:
            by_key[key] = cand
    return list(by_key.values())


async def discover_pool_contractors(
    zipcode: str,
    radius_mi: float = 15.0,
    min_rating: float = 4.0,
    min_reviews: int = 20,
    limit: int = 10,
) -> list[ContractorCandidate]:
    """Discover in-ground pool contractors near ``zipcode``.

    Searches both Yelp and Google Places in parallel, dedupes on
    ``(phone|name)``, filters by ``min_rating`` and ``min_reviews``, and
    returns up to ``limit`` candidates ordered by
    ``rating * log(reviews + 1)`` (desc).
    """
    if not zipcode:
        raise ValueError("zipcode is required")
    if radius_mi <= 0:
        raise ValueError("radius_mi must be positive")
    if limit <= 0:
        return []

    radius_m = int(radius_mi * _MILES_TO_METERS)
    per_source_limit = max(limit * 3, 10)

    yelp_task = _search_yelp(zipcode, radius_m, per_source_limit)
    google_task = _search_google(zipcode, radius_m, per_source_limit)
    # Audit fix (code-review HIGH #7): previously
    # ``return_exceptions=False`` defeated the defensive intent of the
    # per-connector try/except — a surprise exception from one provider
    # would cancel both tasks and crash discovery. Now we keep the
    # results that succeeded and simply log + drop the failures.
    raw_results = await asyncio.gather(
        yelp_task, google_task, return_exceptions=True
    )
    yelp_hits: list[ContractorCandidate] = []
    google_hits: list[ContractorCandidate] = []
    provider_labels = ("yelp", "google_places")
    for label, value in zip(provider_labels, raw_results):
        if isinstance(value, BaseException):
            logger.warning(
                "Discovery provider %s raised during gather: %s", label, value
            )
            continue
        if label == "yelp":
            yelp_hits = list(value)
        else:
            google_hits = list(value)

    merged = _dedup([*yelp_hits, *google_hits])

    filtered = [
        c
        for c in merged
        if c.rating >= min_rating and c.reviews_count >= min_reviews
    ]

    filtered.sort(
        key=lambda c: _rank_score(c.rating, c.reviews_count), reverse=True
    )
    return filtered[:limit]
