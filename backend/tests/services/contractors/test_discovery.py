"""Unit tests for contractor discovery."""
from __future__ import annotations

import math
from typing import Any
from unittest.mock import patch

import pytest

from app.services.contractors import discovery
from app.services.contractors.discovery import (
    ContractorCandidate,
    _dedup,
    _dedup_key,
    _from_google,
    _from_yelp,
    _rank_score,
    discover_pool_contractors,
)
from app.services.data_sources.base_connector import SourceResult


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _yelp_hit(
    *,
    name: str = "BlueWave Pools",
    phone: str = "+1-214-555-0101",
    rating: float = 4.6,
    reviews: int = 120,
    address: str = "100 Main St, Plano, TX 75023",
    url: str = "https://yelp.com/biz/bluewave",
    business_id: str = "yelp_bluewave",
) -> dict[str, Any]:
    return {
        "id": business_id,
        "name": name,
        "rating": rating,
        "review_count": reviews,
        "phone": phone,
        "address": address,
        "url": url,
    }


def _google_hit(
    *,
    name: str = "BlueWave Pools",
    phone: str = "+1 214-555-0101",
    rating: float = 4.6,
    reviews: int = 80,
    address: str = "100 Main St, Plano, TX",
    website: str = "https://bluewavepools.com",
) -> dict[str, Any]:
    return {
        "place_id": "p_bluewave",
        "name": name,
        "phone": phone,
        "address": address,
        "rating": rating,
        "total_ratings": reviews,
        "website": website,
        "business_status": "OPERATIONAL",
    }


# ---------------------------------------------------------------------------
# Pure-function unit tests
# ---------------------------------------------------------------------------


def test_rank_score_combines_rating_and_log_reviews() -> None:
    assert _rank_score(5.0, 0) == 0.0
    assert _rank_score(4.5, 99) == pytest.approx(4.5 * math.log(100), rel=1e-6)
    # higher reviews at same rating => strictly higher score
    assert _rank_score(4.5, 500) > _rank_score(4.5, 100)


def test_dedup_key_uses_phone_when_present() -> None:
    key_a = _dedup_key("BlueWave Pools", "+1-214-555-0101")
    key_b = _dedup_key("bluewave pools", "(214) 555 0101")
    assert key_a == key_b  # same phone digits => same key


def test_dedup_key_falls_back_to_name_when_no_phone() -> None:
    key_a = _dedup_key("BlueWave Pools", "")
    key_b = _dedup_key("BlueWave, Pools!", None)  # type: ignore[arg-type]
    assert key_a == key_b


def test_dedup_prefers_entry_with_more_reviews() -> None:
    a = ContractorCandidate(
        name="BlueWave", phone="", address="", rating=4.5,
        reviews_count=10, source="yelp", business_url="", raw_payload={},
    )
    b = ContractorCandidate(
        name="BlueWave", phone="", address="", rating=4.5,
        reviews_count=200, source="google_places", business_url="",
        raw_payload={},
    )
    merged = _dedup([a, b])
    assert len(merged) == 1
    assert merged[0].reviews_count == 200


def test_from_yelp_drops_rows_missing_signals() -> None:
    assert _from_yelp({"name": "X"}) is None
    assert _from_yelp({"rating": 4.5, "review_count": 10}) is None


def test_from_google_drops_rows_missing_signals() -> None:
    assert _from_google({"name": "X"}) is None
    assert _from_google({"rating": 4.5, "total_ratings": 10}) is None


# ---------------------------------------------------------------------------
# Integration-ish: discover_pool_contractors with both connectors mocked
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_discover_dedupes_across_sources_and_filters() -> None:
    yelp_payload = [
        _yelp_hit(name="BlueWave Pools", rating=4.7, reviews=150),
        _yelp_hit(
            name="TooFewReviews",
            phone="+1-214-555-0200",
            rating=4.8,
            reviews=5,  # below min_reviews=20
            business_id="yelp_tfr",
        ),
    ]
    google_payload = [
        _google_hit(name="BlueWave Pools", rating=4.7, reviews=220),
        _google_hit(
            name="LowRated Pools",
            phone="+1-214-555-0300",
            rating=3.5,  # below min_rating=4.0
            reviews=100,
        ),
        _google_hit(
            name="Quality Pools Co",
            phone="+1-214-555-0400",
            rating=4.9,
            reviews=40,
        ),
    ]

    async def fake_yelp(zip_, radius, limit):
        return [c for c in (_from_yelp(h) for h in yelp_payload) if c]

    async def fake_google(zip_, radius, limit):
        return [c for c in (_from_google(h) for h in google_payload) if c]

    with (
        patch.object(discovery, "_search_yelp", fake_yelp),
        patch.object(discovery, "_search_google", fake_google),
    ):
        results = await discover_pool_contractors(
            zipcode="75023",
            radius_mi=15.0,
            min_rating=4.0,
            min_reviews=20,
            limit=10,
        )

    names = [c.name for c in results]
    # BlueWave deduped to a single entry, TooFewReviews filtered,
    # LowRated filtered, Quality Pools retained.
    assert names == ["BlueWave Pools", "Quality Pools Co"] or names == [
        "Quality Pools Co",
        "BlueWave Pools",
    ]
    # BlueWave should rank ahead — same rating, more reviews.
    assert names[0] == "BlueWave Pools"
    # Deduped BlueWave should retain the higher review_count (Google=220)
    bluewave = next(c for c in results if c.name == "BlueWave Pools")
    assert bluewave.reviews_count == 220


@pytest.mark.asyncio
async def test_discover_respects_limit() -> None:
    hits = [
        _yelp_hit(
            name=f"Pool Co {i}",
            phone=f"+1-214-555-{i:04d}",
            rating=4.5,
            reviews=100 + i,
            business_id=f"yelp_{i}",
        )
        for i in range(10)
    ]

    async def fake_yelp(zip_, radius, limit):
        return [c for c in (_from_yelp(h) for h in hits) if c]

    async def fake_google(zip_, radius, limit):
        return []

    with (
        patch.object(discovery, "_search_yelp", fake_yelp),
        patch.object(discovery, "_search_google", fake_google),
    ):
        results = await discover_pool_contractors(
            zipcode="75023", limit=3
        )
    assert len(results) == 3


@pytest.mark.asyncio
async def test_discover_raises_on_blank_zip() -> None:
    with pytest.raises(ValueError):
        await discover_pool_contractors(zipcode="")


@pytest.mark.asyncio
async def test_discover_with_both_sources_down_returns_empty() -> None:
    async def failing(zip_, radius, limit):
        return []

    with (
        patch.object(discovery, "_search_yelp", failing),
        patch.object(discovery, "_search_google", failing),
    ):
        results = await discover_pool_contractors(zipcode="75023")
    assert results == []


# ---------------------------------------------------------------------------
# SourceResult shape is not directly consumed by discover — this covers
# the real Yelp/Google connector adapter functions.
# ---------------------------------------------------------------------------


def test_source_result_roundtrip() -> None:
    """Sanity: the normalized payloads used above match SourceResult."""
    sr = SourceResult(
        data=[_yelp_hit()],
        raw_response=None,
        total_results=1,
        source_name="Yelp",
    )
    assert sr.total_results == 1
    first = sr.data[0]
    assert _from_yelp(first) is not None
