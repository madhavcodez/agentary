"""Rule-based backyard segmentation (Pool Concierge v1).

Given a parcel polygon plus house and (optional) driveway footprint
rectangles, compute the GeoJSON polygon of the "backyard" — the region
behind the house — and its area in square feet.

No ML: subtract house + driveway from the parcel, pick the largest
contiguous remaining component whose centroid sits behind the house
(relative to the parcel's longest axis), and return that.
"""

from __future__ import annotations

import math
from typing import Any

from shapely.geometry import MultiPolygon, Polygon, mapping, shape
from shapely.ops import unary_union

# Rough degrees-to-feet conversion at Plano TX latitude (~33° N).
# Used only when coordinates look like WGS84 (|lon| <= 180, |lat| <= 90).
_FT_PER_DEG_LAT = 364_000.0
_FT_PER_DEG_LON = 305_000.0


def _is_lonlat(polygon: Polygon) -> bool:
    """Heuristic: treat coords as WGS84 degrees if they fit standard ranges
    AND the polygon extent is fractional (a real parcel is <0.5 deg).

    Raw feet-scale coordinates (e.g. a 60x80 ft rectangle at origin) also
    fit the ``[-180, 180]`` degree bounds, so we need the extent check to
    avoid false positives.
    """
    minx, miny, maxx, maxy = polygon.bounds
    in_range = (
        -180.0 <= minx <= 180.0
        and -90.0 <= miny <= 90.0
        and -180.0 <= maxx <= 180.0
        and -90.0 <= maxy <= 90.0
    )
    if not in_range:
        return False
    extent_deg = max(maxx - minx, maxy - miny)
    return extent_deg < 0.5


def _area_sqft(polygon: Polygon) -> float:
    """Return polygon area in square feet.

    Treats coordinates as WGS84 degrees when possible and projects to feet
    at the polygon's latitude. Otherwise assumes the input is already in
    feet.
    """
    if polygon.is_empty:
        return 0.0
    if _is_lonlat(polygon):
        cy = polygon.centroid.y
        ft_per_deg_lat = _FT_PER_DEG_LAT
        ft_per_deg_lon = 69.172 * 5280 * math.cos(math.radians(cy))
        return float(polygon.area) * ft_per_deg_lat * ft_per_deg_lon
    return float(polygon.area)


def _to_polygon(geojson_or_coords: Any) -> Polygon:
    """Accept GeoJSON dict or raw coord ring and return a shapely Polygon."""
    if isinstance(geojson_or_coords, dict) and "coordinates" in geojson_or_coords:
        return shape(geojson_or_coords)
    if isinstance(geojson_or_coords, (list, tuple)):
        # Assume a coordinate ring.
        return Polygon(geojson_or_coords)
    raise TypeError(
        f"Unsupported polygon/rect input: {type(geojson_or_coords)!r}"
    )


def _house_centroid_side(
    parcel: Polygon, house: Polygon
) -> tuple[str, float]:
    """Classify which "side" of the parcel the house sits on.

    Returns ("x" or "y", house_center) — the axis with the greater parcel
    extent (street-facing) and the house centroid along that axis. A
    backyard candidate is then the side of the parcel opposite the house.
    """
    minx, miny, maxx, maxy = parcel.bounds
    width = maxx - minx
    height = maxy - miny
    if width >= height:
        return ("x", house.centroid.x)
    return ("y", house.centroid.y)


def _is_behind_house(
    candidate: Polygon,
    parcel: Polygon,
    house: Polygon,
) -> bool:
    """True if *candidate*'s centroid sits on the side of the parcel
    opposite the house's centroid along the parcel's short axis."""
    minx, miny, maxx, maxy = parcel.bounds
    axis, house_center = _house_centroid_side(parcel, house)
    cand_c = candidate.centroid
    if axis == "x":
        parcel_mid = (minx + maxx) / 2.0
        house_side = house_center >= parcel_mid
        cand_side = cand_c.x >= parcel_mid
    else:
        parcel_mid = (miny + maxy) / 2.0
        house_side = house_center >= parcel_mid
        cand_side = cand_c.y >= parcel_mid
    return cand_side != house_side


def segment_backyard(
    parcel_polygon: Any,
    house_footprint_rect: Any,
    driveway_rect: Any | None = None,
) -> dict[str, Any]:
    """Compute backyard GeoJSON polygon + square footage.

    Args:
        parcel_polygon: GeoJSON Polygon dict or shapely-compatible coord list.
        house_footprint_rect: GeoJSON Polygon dict or coord list for the
            house footprint.
        driveway_rect: Optional GeoJSON Polygon / coord list for the driveway.

    Returns:
        ``{"backyard_polygon": GeoJSON Polygon, "backyard_sqft": float}``.
        Falls back to an empty polygon and 0.0 sqft if the subtraction
        produces no usable region.
    """
    parcel = _to_polygon(parcel_polygon)
    house = _to_polygon(house_footprint_rect)

    subtract = [house]
    if driveway_rect is not None:
        subtract.append(_to_polygon(driveway_rect))

    # Clip subtractions to the parcel first.
    clipped_sub = [parcel.intersection(s) for s in subtract if not s.is_empty]
    subtract_union = unary_union(clipped_sub) if clipped_sub else None

    if subtract_union is None or subtract_union.is_empty:
        remainder = parcel
    else:
        remainder = parcel.difference(subtract_union)

    # Collect polygon components.
    if isinstance(remainder, MultiPolygon):
        parts = list(remainder.geoms)
    elif isinstance(remainder, Polygon):
        parts = [remainder] if not remainder.is_empty else []
    else:
        parts = [
            g
            for g in getattr(remainder, "geoms", [])
            if isinstance(g, Polygon) and not g.is_empty
        ]

    if not parts:
        empty_poly = {"type": "Polygon", "coordinates": []}
        return {"backyard_polygon": empty_poly, "backyard_sqft": 0.0}

    behind = [p for p in parts if _is_behind_house(p, parcel, house)]
    candidates = behind if behind else parts
    backyard = max(candidates, key=lambda p: p.area)

    backyard_sqft = _area_sqft(backyard)
    return {
        "backyard_polygon": mapping(backyard),
        "backyard_sqft": float(backyard_sqft),
    }
