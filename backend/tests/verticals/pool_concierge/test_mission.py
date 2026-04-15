"""End-to-end test of the Pool Concierge mission with all connectors mocked."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.services.data_sources.base_connector import SourceResult
from app.verticals.pool_concierge.mission import (
    ScoredListing,
    run_pool_concierge_mission,
)


class _FakeZillow:
    """Stub Zillow connector yielding three deterministic listings."""

    name = "Zillow"
    provider = "zillow"
    description = ""

    def __init__(self) -> None:
        self._listings = [
            {
                "zpid": "z-1",
                "address": "1001 Independence Pkwy, Plano, TX 75075",
                "price": 850_000,
                "url": "https://zillow.com/1",
            },
            {
                "zpid": "z-2",
                "address": "2025 Legacy Dr, Plano, TX 75024",
                "price": 1_100_000,
                "url": "https://zillow.com/2",
            },
            {
                "zpid": "z-3",
                "address": "700 Tiny Ct, Plano, TX 75023",
                "price": 520_000,
                "url": "https://zillow.com/3",
            },
        ]

    async def search(self, query: str, **kwargs: Any) -> SourceResult:
        return SourceResult(
            data=list(self._listings),
            raw_response=None,
            total_results=len(self._listings),
            source_name=self.name,
        )


class _FakeAttom:
    """Stub ATTOM returning distinct property detail per address."""

    name = "ATTOM"

    _DETAILS = {
        "z-1": {
            "lot_size_sqft": 12_000.0,
            "building_footprint_sqft": 2_200.0,
            "year_built": 2005,
            "stories": 1.0,
            "lot_dimensions": "80x150",
        },
        "z-2": {
            "lot_size_sqft": 18_000.0,
            "building_footprint_sqft": 3_000.0,
            "year_built": 2012,
            "stories": 2.0,
            "lot_dimensions": "90x200",
        },
        "z-3": {
            "lot_size_sqft": 4_500.0,
            "building_footprint_sqft": 1_800.0,
            "year_built": 1998,
            "stories": 1.0,
            "lot_dimensions": "50x90",
        },
    }

    async def get_property_detail(self, address: str) -> SourceResult:
        key = "z-3"
        if "Independence" in address:
            key = "z-1"
        elif "Legacy" in address:
            key = "z-2"
        return SourceResult(
            data=[self._DETAILS[key]],
            raw_response=None,
            total_results=1,
            source_name=self.name,
        )


class _FakeRegrid:
    """Stub Regrid producing lon/lat parcel rectangles sized to the address."""

    name = "Regrid"

    async def get_parcel_polygon(self, address: str) -> SourceResult:
        if "Independence" in address:
            width_ft, depth_ft = 80.0, 150.0
        elif "Legacy" in address:
            width_ft, depth_ft = 90.0, 200.0
        else:
            width_ft, depth_ft = 50.0, 90.0
        cx, cy = -96.70, 33.02
        dlon = (width_ft / 2.0) / 305_000.0
        dlat = (depth_ft / 2.0) / 364_000.0
        polygon = {
            "type": "Polygon",
            "coordinates": [
                [
                    [cx - dlon, cy - dlat],
                    [cx + dlon, cy - dlat],
                    [cx + dlon, cy + dlat],
                    [cx - dlon, cy + dlat],
                    [cx - dlon, cy - dlat],
                ]
            ],
        }
        return SourceResult(
            data=[{"polygon": polygon}],
            raw_response=None,
            total_results=1,
            source_name=self.name,
        )


class _FakeMapbox:
    """Stub Mapbox returning a tiny PNG + deterministic URL."""

    name = "Mapbox Satellite"

    async def get_aerial_image(
        self,
        bbox: tuple[float, float, float, float],
        *,
        zoom: int = 20,
        size: tuple[int, int] = (1024, 1024),
    ) -> SourceResult:
        return SourceResult(
            data=[{"image_bytes": b"PNG", "format": "png"}],
            raw_response=None,
            total_results=1,
            source_name=self.name,
            source_url="https://mock.mapbox/tile.png",
            metadata={"bbox": list(bbox), "zoom": zoom},
        )


@pytest.mark.asyncio
async def test_mission_pipeline_produces_ranked_output() -> None:
    results = await run_pool_concierge_mission(
        zipcode="75024",
        radius_mi=5.0,
        max_listings=10,
        db=None,
        zillow=_FakeZillow(),
        attom=_FakeAttom(),
        regrid=_FakeRegrid(),
        mapbox=_FakeMapbox(),
    )

    assert isinstance(results, list)
    assert len(results) >= 2
    for r in results:
        assert isinstance(r, ScoredListing)
    # Sorted descending by score.
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)
    # Largest lot (Legacy Dr) should outrank the tiny lot.
    addresses = [r.address for r in results]
    assert any("Legacy" in a for a in addresses)
    legacy_score = next(r.score for r in results if "Legacy" in r.address)
    tiny_score = next(
        (r.score for r in results if "Tiny" in r.address), 0.0
    )
    assert legacy_score >= tiny_score


@pytest.mark.asyncio
async def test_mission_respects_max_listings_cap() -> None:
    results = await run_pool_concierge_mission(
        zipcode="75024",
        radius_mi=5.0,
        max_listings=2,
        db=None,
        zillow=_FakeZillow(),
        attom=_FakeAttom(),
        regrid=_FakeRegrid(),
        mapbox=_FakeMapbox(),
    )
    assert len(results) <= 2


@pytest.mark.asyncio
async def test_scored_listing_carries_polygons_and_placement() -> None:
    results = await run_pool_concierge_mission(
        zipcode="75024",
        radius_mi=5.0,
        max_listings=5,
        db=None,
        zillow=_FakeZillow(),
        attom=_FakeAttom(),
        regrid=_FakeRegrid(),
        mapbox=_FakeMapbox(),
    )
    assert results
    top = results[0]
    assert top.parcel_polygon.get("type") == "Polygon"
    assert top.backyard_polygon.get("type") == "Polygon"
    assert "width_ft" in top.pool_placement
    assert "length_ft" in top.pool_placement
    assert top.aerial_image_url == "https://mock.mapbox/tile.png"
    d = top.to_dict()
    assert d["score"] == top.score
    assert d["address"] == top.address
