"""Deterministic pool placement heuristic.

Finds the largest pool rectangle that fits inside a backyard polygon
subject to setback constraints. Starts with an axis-aligned grid search
at 1 ft resolution, then tries 15° rotations to see if a tilted
rectangle clears more area. No LLM / ML — pure geometry.

The width:length ratio of returned pool rectangles is clamped between
1:1 and 1:2.5 so we don't recommend pencil-thin ribbons of water.
"""

from __future__ import annotations

import math
from typing import Any

from shapely.affinity import rotate, translate
from shapely.geometry import Polygon, box, shape


_FT_PER_DEG_LAT = 364_000.0
_DEG_PER_FT_LAT = 1.0 / _FT_PER_DEG_LAT


def _is_lonlat(polygon: Polygon) -> bool:
    """Treat a polygon as WGS84 when bounds fit degree ranges AND extents
    are fractional-degree (a real parcel is <0.5 deg across)."""
    minx, miny, maxx, maxy = polygon.bounds
    in_range = (
        -180.0 <= minx <= 180.0
        and -90.0 <= miny <= 90.0
        and -180.0 <= maxx <= 180.0
        and -90.0 <= maxy <= 90.0
    )
    if not in_range:
        return False
    # Parcel extent in degrees — a realistic lot is <<0.5 deg. Anything
    # larger is almost certainly raw-feet coordinates that happen to fit
    # the degree bounds.
    extent_deg = max(maxx - minx, maxy - miny)
    return extent_deg < 0.5


def _to_polygon(geojson_or_shapely: Any) -> Polygon:
    if hasattr(geojson_or_shapely, "geom_type"):
        return geojson_or_shapely
    if isinstance(geojson_or_shapely, dict) and "coordinates" in geojson_or_shapely:
        return shape(geojson_or_shapely)
    if isinstance(geojson_or_shapely, (list, tuple)):
        return Polygon(geojson_or_shapely)
    raise TypeError(
        f"Unsupported polygon input: {type(geojson_or_shapely)!r}"
    )


def _ft_per_deg_lon(lat_deg: float) -> float:
    """Approximate feet per degree of longitude at *lat_deg*."""
    return 69.172 * 5280.0 * math.cos(math.radians(lat_deg))


def _project_ll_to_ft(polygon: Polygon) -> tuple[Polygon, tuple[float, float, float, float]]:
    """Project a lon/lat polygon to a local feet frame.

    Returns (projected_polygon, (origin_lon, origin_lat, ft_per_deg_lon, ft_per_deg_lat)).
    """
    minx, miny, maxx, maxy = polygon.bounds
    origin_lon = minx
    origin_lat = miny
    ft_per_deg_lon = _ft_per_deg_lon((miny + maxy) / 2.0)
    ft_per_deg_lat = _FT_PER_DEG_LAT
    exterior = [
        (
            (x - origin_lon) * ft_per_deg_lon,
            (y - origin_lat) * ft_per_deg_lat,
        )
        for x, y in polygon.exterior.coords
    ]
    interiors: list[list[tuple[float, float]]] = []
    for ring in polygon.interiors:
        interiors.append(
            [
                (
                    (x - origin_lon) * ft_per_deg_lon,
                    (y - origin_lat) * ft_per_deg_lat,
                )
                for x, y in ring.coords
            ]
        )
    projected = Polygon(exterior, holes=interiors)
    return projected, (origin_lon, origin_lat, ft_per_deg_lon, ft_per_deg_lat)


def _unproject_ft_to_ll(
    center_ft_x: float,
    center_ft_y: float,
    frame: tuple[float, float, float, float],
) -> tuple[float, float]:
    origin_lon, origin_lat, ft_per_deg_lon, ft_per_deg_lat = frame
    lon = origin_lon + (center_ft_x / ft_per_deg_lon)
    lat = origin_lat + (center_ft_y / ft_per_deg_lat)
    return lat, lon


def _clamp_ratio(width: float, length: float) -> tuple[float, float]:
    """Clamp width:length to the range [1:1, 1:2.5]."""
    if length <= 0 or width <= 0:
        return width, length
    w, l = sorted([width, length])  # w <= l
    ratio = l / w
    if ratio > 2.5:
        l = w * 2.5
    return w, l


def _rect_fits(search_area: Polygon, cx: float, cy: float, w: float, l: float) -> bool:
    """Check if an axis-aligned rectangle with lower-left (cx, cy) fits."""
    rect = box(cx, cy, cx + w, cy + l)
    return search_area.contains(rect)


def _scan_at_dims(
    search_area: Polygon,
    bbox: tuple[float, float, float, float],
    w: float,
    l: float,
    coarse_step: float,
) -> tuple[float, float] | None:
    """Find any lower-left corner where a w x l rectangle fits inside
    search_area. Returns (cx, cy) or None.
    """
    minx, miny, maxx, maxy = bbox
    if w > maxx - minx or l > maxy - miny:
        return None
    cy = miny
    while cy + l <= maxy + 1e-6:
        cx = minx
        while cx + w <= maxx + 1e-6:
            if _rect_fits(search_area, cx, cy, w, l):
                return (cx, cy)
            cx += coarse_step
        cy += coarse_step
    return None


def _axis_aligned_scan(
    search_area: Polygon,
    bbox: tuple[float, float, float, float],
    min_width: float = 8.0,
    max_width: float = 30.0,
    min_length: float = 10.0,
    max_length: float = 50.0,
    step_ft: float = 1.0,
) -> dict[str, Any] | None:
    """Grid search for the largest axis-aligned rectangle inside *search_area*.

    Enumerates candidate (w, l) pairs in descending-area order, and for
    each pair sweeps the lower-left corner across the bbox at 1ft
    resolution. The first (w, l) with any fitting corner wins because
    all later candidates have smaller area.
    """
    minx, miny, maxx, maxy = bbox
    avail_w = maxx - minx
    avail_l = maxy - miny
    if avail_w < min_width or avail_l < min_length:
        return None

    # Build (w, l) candidate list, ratio-clamped, largest area first.
    candidates: list[tuple[float, float, float]] = []
    w = min(max_width, avail_w)
    while w >= min_width - 1e-6:
        l = min(max_length, avail_l)
        while l >= min_length - 1e-6:
            cw, cl = _clamp_ratio(w, l)
            if abs(cw - w) < 1e-6 and abs(cl - l) < 1e-6:
                candidates.append((w * l, float(w), float(l)))
            l -= step_ft
        w -= step_ft

    # Also consider (l, w) orientation swapped — a vertical pool vs horizontal.
    swapped = [(a, l, w) for a, w, l in candidates]
    all_candidates = sorted(candidates + swapped, key=lambda t: -t[0])

    for _area, w, l in all_candidates:
        corner = _scan_at_dims(search_area, bbox, w, l, coarse_step=step_ft)
        if corner is not None:
            cx, cy = corner
            return {
                "center_x": cx + w / 2.0,
                "center_y": cy + l / 2.0,
                "width_ft": float(w),
                "length_ft": float(l),
                "area_ft2": float(w * l),
            }
    return None


def _rotated_scan(
    search_area: Polygon,
    bbox: tuple[float, float, float, float],
    angle_deg: float,
    baseline_area: float,
    min_width: float = 8.0,
    max_width: float = 30.0,
    min_length: float = 10.0,
    max_length: float = 50.0,
    step_ft: float = 2.0,
) -> dict[str, Any] | None:
    """Test rotated rectangles at *angle_deg* to see if they beat baseline."""
    cx0 = (bbox[0] + bbox[2]) / 2.0
    cy0 = (bbox[1] + bbox[3]) / 2.0

    # Rotate the search polygon so we can keep testing axis-aligned rects.
    rotated_area = rotate(
        search_area, -angle_deg, origin=(cx0, cy0), use_radians=False
    )
    r_bbox = rotated_area.bounds
    avail_w = r_bbox[2] - r_bbox[0]
    avail_l = r_bbox[3] - r_bbox[1]
    if avail_w < min_width or avail_l < min_length:
        return None

    # Build candidate list, descending area, ratio-clamped.
    cand: list[tuple[float, float, float]] = []
    w = min(max_width, avail_w)
    while w >= min_width - 1e-6:
        l = min(max_length, avail_l)
        while l >= min_length - 1e-6:
            cw, cl = _clamp_ratio(w, l)
            if abs(cw - w) < 1e-6 and abs(cl - l) < 1e-6 and w * l > baseline_area:
                cand.append((w * l, float(w), float(l)))
            l -= step_ft
        w -= step_ft

    swapped = [(a, l, w) for a, w, l in cand]
    all_cand = sorted(cand + swapped, key=lambda t: -t[0])

    for _a, w, l in all_cand:
        corner = _scan_at_dims(rotated_area, r_bbox, w, l, coarse_step=step_ft)
        if corner is None:
            continue
        cx, cy = corner
        center_x_rot = cx + w / 2.0
        center_y_rot = cy + l / 2.0
        dx = center_x_rot - cx0
        dy = center_y_rot - cy0
        theta = math.radians(angle_deg)
        orig_x = cx0 + dx * math.cos(theta) - dy * math.sin(theta)
        orig_y = cy0 + dx * math.sin(theta) + dy * math.cos(theta)
        return {
            "center_x": orig_x,
            "center_y": orig_y,
            "width_ft": float(w),
            "length_ft": float(l),
            "area_ft2": float(w * l),
            "rotation_deg": float(angle_deg),
        }
    return None


def find_largest_pool_rectangle(
    backyard_polygon: Any,
    *,
    min_setback_ft: float = 5.0,
    house_setback_ft: float = 10.0,
) -> dict[str, Any]:
    """Return the largest placeable pool rectangle inside *backyard_polygon*.

    Args:
        backyard_polygon: GeoJSON Polygon dict or shapely Polygon.
        min_setback_ft: Buffer from every backyard edge (property lines).
        house_setback_ft: Additional buffer applied to the whole
            backyard interior to conservatively keep the pool clear of
            the house line as well.

    Returns:
        ``{center_lat, center_lon, width_ft, length_ft, rotation_deg}``.
        ``center_lat`` / ``center_lon`` are ``None`` when the input
        polygon is not in WGS84 coordinates (e.g. unit tests with a
        synthetic feet-scale polygon). Zero-sized result returned when
        no rectangle fits after setbacks.
    """
    polygon = _to_polygon(backyard_polygon)
    empty = {
        "center_lat": None,
        "center_lon": None,
        "width_ft": 0.0,
        "length_ft": 0.0,
        "rotation_deg": 0.0,
    }

    if polygon.is_empty or polygon.area <= 0:
        return empty

    is_ll = _is_lonlat(polygon)
    if is_ll:
        working, frame = _project_ll_to_ft(polygon)
    else:
        working = polygon
        frame = None

    # Apply combined setback (house_setback dominates min_setback).
    setback = max(min_setback_ft, house_setback_ft)
    search_area = working.buffer(-setback)

    if search_area.is_empty or search_area.area <= 0:
        return empty

    # Shapely can return a MultiPolygon after buffer(-).
    if search_area.geom_type == "MultiPolygon":
        search_area = max(search_area.geoms, key=lambda p: p.area)

    bbox = search_area.bounds
    axis_result = _axis_aligned_scan(search_area, bbox)
    if axis_result is None:
        return empty

    best = dict(axis_result)
    best["rotation_deg"] = 0.0

    # Try 15° rotations to see if we can do better.
    baseline_area = best["area_ft2"]
    for angle in (15.0, 30.0, 45.0, 60.0, 75.0):
        rotated = _rotated_scan(
            search_area,
            bbox,
            angle_deg=angle,
            baseline_area=baseline_area,
        )
        if rotated is not None and rotated["area_ft2"] > best["area_ft2"]:
            best = rotated
            baseline_area = best["area_ft2"]

    # Translate the center back out to lat/lon if we projected.
    if is_ll and frame is not None:
        lat, lon = _unproject_ft_to_ll(
            best["center_x"], best["center_y"], frame
        )
    else:
        lat = None
        lon = None

    return {
        "center_lat": lat,
        "center_lon": lon,
        "width_ft": float(best["width_ft"]),
        "length_ft": float(best["length_ft"]),
        "rotation_deg": float(best.get("rotation_deg", 0.0)),
    }
