"""Pool Concierge end-to-end mission template.

Pulls single-family on-market listings for a ZIP code, enriches each
with ATTOM property detail, Regrid parcel polygon, Mapbox aerial tile,
segments the backyard, places a candidate pool, and scores fit.
Returns the top N ranked ``ScoredListing`` records.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from ...config import settings
from ...services.cv.backyard_segmenter import segment_backyard
from ...services.data_sources.connectors.attom import AttomConnector
from ...services.data_sources.connectors.mapbox_satellite import (
    MapboxSatelliteConnector,
)
from ...services.data_sources.connectors.regrid import RegridConnector
from ...services.data_sources.connectors.zillow import ZillowConnector
from .pool_placement import find_largest_pool_rectangle
from .scoring import score_pool_fitness


@dataclass(frozen=True)
class ScoredListing:
    """Single enriched, scored listing returned by the pool mission."""

    listing_url: str
    address: str
    list_price: float | None
    lot_size_sqft: float | None
    building_footprint_sqft: float | None
    backyard_sqft: float
    parcel_polygon: dict[str, Any]
    backyard_polygon: dict[str, Any]
    pool_placement: dict[str, Any]
    score: float
    fit_reason: str
    max_pool_size: str
    aerial_image_url: str | None
    zpid: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "listing_url": self.listing_url,
            "address": self.address,
            "list_price": self.list_price,
            "lot_size_sqft": self.lot_size_sqft,
            "building_footprint_sqft": self.building_footprint_sqft,
            "backyard_sqft": self.backyard_sqft,
            "parcel_polygon": self.parcel_polygon,
            "backyard_polygon": self.backyard_polygon,
            "pool_placement": self.pool_placement,
            "score": self.score,
            "fit_reason": self.fit_reason,
            "max_pool_size": self.max_pool_size,
            "aerial_image_url": self.aerial_image_url,
            "zpid": self.zpid,
        }


def _polygon_bbox(polygon: dict[str, Any]) -> tuple[float, float, float, float]:
    """Return (min_lon, min_lat, max_lon, max_lat) for a GeoJSON Polygon."""
    coords = polygon.get("coordinates") or []
    if not coords:
        return (0.0, 0.0, 0.0, 0.0)
    ring = coords[0]
    xs = [pt[0] for pt in ring]
    ys = [pt[1] for pt in ring]
    return (min(xs), min(ys), max(xs), max(ys))


def _rect_from_bbox_center(
    center_lon: float,
    center_lat: float,
    width_ft: float,
    depth_ft: float,
) -> dict[str, Any]:
    """Build a GeoJSON Polygon rectangle centered on (lon, lat)."""
    deg_per_ft_lat = 1.0 / 364_000.0
    deg_per_ft_lon = 1.0 / 305_000.0
    half_lat = (depth_ft / 2.0) * deg_per_ft_lat
    half_lon = (width_ft / 2.0) * deg_per_ft_lon
    ring = [
        [center_lon - half_lon, center_lat - half_lat],
        [center_lon + half_lon, center_lat - half_lat],
        [center_lon + half_lon, center_lat + half_lat],
        [center_lon - half_lon, center_lat + half_lat],
        [center_lon - half_lon, center_lat - half_lat],
    ]
    return {"type": "Polygon", "coordinates": [ring]}


def _infer_house_rect(
    parcel_polygon: dict[str, Any],
    footprint_sqft: float | None,
) -> dict[str, Any]:
    """Approximate the house footprint as a rectangle near the parcel's
    street-facing edge.

    The real pipeline will replace this with a segmentation mask from the
    Mapbox aerial tile, but a deterministic placeholder lets the rest of
    the pipeline work end-to-end today.
    """
    bbox = _polygon_bbox(parcel_polygon)
    min_lon, min_lat, max_lon, max_lat = bbox
    center_lon = (min_lon + max_lon) / 2.0
    street_lat = min_lat + (max_lat - min_lat) * 0.20  # front 20% of lot
    # Derive rectangle dimensions from footprint sqft; fall back to 40x30.
    fp = float(footprint_sqft or 1_800.0)
    width_ft = max(25.0, min(90.0, (fp ** 0.5) * 1.25))
    depth_ft = max(20.0, fp / max(width_ft, 1.0))
    return _rect_from_bbox_center(center_lon, street_lat, width_ft, depth_ft)


async def _process_listing(
    listing: dict[str, Any],
    *,
    attom: AttomConnector,
    regrid: RegridConnector,
    mapbox: MapboxSatelliteConnector,
    semaphore: asyncio.Semaphore,
) -> ScoredListing | None:
    """Enrich + score a single listing. Returns None on total failure.

    Audit fix (code-review HIGH #4): short-circuit when the segmented
    backyard has zero area — placement on an empty polygon produces
    meaningless (0x0) rectangles that pollute downstream scoring.
    """
    address = listing.get("address") or ""
    if not address:
        return None

    async with semaphore:
        try:
            detail_result = await attom.get_property_detail(address)
            parcel_result = await regrid.get_parcel_polygon(address)
        except Exception:
            return None

        detail = (detail_result.data or [{}])[0]
        parcel_entry = (parcel_result.data or [{}])[0]
        parcel_polygon = parcel_entry.get("polygon")
        if not parcel_polygon:
            return None

        bbox = _polygon_bbox(parcel_polygon)

        try:
            aerial_result = await mapbox.get_aerial_image(bbox=bbox, zoom=20)
        except Exception:
            aerial_result = None

    footprint_sqft = detail.get("building_footprint_sqft")
    house_rect = _infer_house_rect(parcel_polygon, footprint_sqft)

    seg = segment_backyard(parcel_polygon, house_rect)
    backyard_polygon = seg["backyard_polygon"]
    backyard_sqft = seg["backyard_sqft"]

    # Audit fix (code-review HIGH #4): skip listings where the house
    # covers the entire parcel / backyard polygon has no interior.
    if float(backyard_sqft or 0.0) <= 0.0:
        return None

    placement = find_largest_pool_rectangle(
        backyard_polygon,
        min_setback_ft=5.0,
        house_setback_ft=10.0,
    )

    fitness = score_pool_fitness(
        backyard_sqft=backyard_sqft,
        max_pool_dims={
            "width_ft": placement.get("width_ft", 0.0),
            "length_ft": placement.get("length_ft", 0.0),
        },
    )

    aerial_url = None
    if aerial_result is not None:
        aerial_url = aerial_result.source_url

    return ScoredListing(
        listing_url=listing.get("url") or "",
        address=address,
        list_price=(
            float(listing["price"]) if listing.get("price") is not None else None
        ),
        lot_size_sqft=(
            float(detail["lot_size_sqft"])
            if detail.get("lot_size_sqft") is not None
            else None
        ),
        building_footprint_sqft=(
            float(detail["building_footprint_sqft"])
            if detail.get("building_footprint_sqft") is not None
            else None
        ),
        backyard_sqft=float(backyard_sqft),
        parcel_polygon=parcel_polygon,
        backyard_polygon=backyard_polygon,
        pool_placement=placement,
        score=float(fitness["score"]),
        fit_reason=str(fitness["fit_reason"]),
        max_pool_size=str(fitness["max_pool_size"]),
        aerial_image_url=aerial_url,
        zpid=listing.get("zpid"),
    )


async def run_pool_concierge_mission(
    zipcode: str,
    radius_mi: float = 5.0,
    max_listings: int = 10,
    db: Session | None = None,
    *,
    zillow: ZillowConnector | None = None,
    attom: AttomConnector | None = None,
    regrid: RegridConnector | None = None,
    mapbox: MapboxSatelliteConnector | None = None,
) -> list[ScoredListing]:
    """Run the Pool Concierge pipeline and return top ``max_listings``.

    Args:
        zipcode: Target US ZIP code, e.g. ``"75024"``.
        radius_mi: Search radius in miles (plumbed through to Zillow).
        max_listings: Cap on returned scored listings.
        db: Optional DB session reserved for persistence wiring.
        zillow, attom, regrid, mapbox: Optional preconstructed connectors
            (used by tests / DI). Defaults wire from ``settings``.

    Returns:
        ``ScoredListing`` records sorted by ``score`` descending.
    """
    zillow = zillow or ZillowConnector(api_key=settings.zillow_api_key)
    attom = attom or AttomConnector(api_key=settings.attom_api_key)
    regrid = regrid or RegridConnector(api_key=settings.regrid_api_key)
    mapbox = mapbox or MapboxSatelliteConnector(token=settings.mapbox_token)

    # Audit fix (code-review HIGH #2): ensure the three connector HTTP
    # clients are closed even on exceptions. Wrap the mission body in
    # try/finally and best-effort close each connector at the end.
    try:
        min_price = settings.pool_concierge_min_budget_usd
        max_price = settings.pool_concierge_max_budget_usd

        search_result = await zillow.search(
            zipcode,
            location=zipcode,
            price_min=min_price,
            price_max=max_price,
            property_type="house",
            status="for_sale",
            radius=radius_mi,
        )
        listings = list(search_result.data or [])

        # Hard cap how many listings we enrich to stay under API quotas.
        # Audit fix (code-review HIGH #3): the previous
        # ``max(max_listings * 2, max_listings)`` was always ``max_listings * 2``
        # — a no-op ``max``. Keep the buffer-then-rank intent (fetch 2x
        # so ranking has headroom) but state it plainly.
        cap = max_listings * 2
        listings = listings[:cap]

        semaphore = asyncio.Semaphore(5)
        tasks = [
            _process_listing(
                listing,
                attom=attom,
                regrid=regrid,
                mapbox=mapbox,
                semaphore=semaphore,
            )
            for listing in listings
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        scored: list[ScoredListing] = []
        for r in results:
            if isinstance(r, ScoredListing):
                scored.append(r)

        scored.sort(key=lambda s: s.score, reverse=True)
        return scored[:max_listings]
    finally:
        for connector in (attom, regrid, mapbox):
            aclose = getattr(connector, "aclose", None)
            if aclose is None:
                continue
            try:
                await aclose()
            except Exception:  # noqa: BLE001 — best-effort cleanup
                pass
