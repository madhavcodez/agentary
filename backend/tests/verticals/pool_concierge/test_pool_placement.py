"""Unit tests for Pool Concierge pool placement."""

from __future__ import annotations

from app.verticals.pool_concierge.pool_placement import (
    find_largest_pool_rectangle,
)


def _rect_polygon(width_ft: float, length_ft: float) -> dict:
    """Synthetic feet-scale backyard polygon (origin at 0,0)."""
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [0.0, 0.0],
                [width_ft, 0.0],
                [width_ft, length_ft],
                [0.0, length_ft],
                [0.0, 0.0],
            ]
        ],
    }


def test_large_yard_fits_20x40_pool() -> None:
    yard = _rect_polygon(width_ft=60.0, length_ft=80.0)
    result = find_largest_pool_rectangle(
        yard, min_setback_ft=5.0, house_setback_ft=10.0
    )
    # Usable area after 10ft setback: 40x60 ft -> plenty for 20x40.
    short = min(result["width_ft"], result["length_ft"])
    long_ = max(result["width_ft"], result["length_ft"])
    assert short >= 20.0
    assert long_ >= 40.0
    # No lat/lon for synthetic feet polygon.
    assert result["center_lat"] is None
    assert result["center_lon"] is None


def test_tiny_yard_returns_empty_pool() -> None:
    # Smaller than twice the setback → no usable area at all.
    yard = _rect_polygon(width_ft=12.0, length_ft=12.0)
    result = find_largest_pool_rectangle(
        yard, min_setback_ft=5.0, house_setback_ft=10.0
    )
    assert result["width_ft"] == 0.0
    assert result["length_ft"] == 0.0


def test_medium_yard_fits_15x30_pool() -> None:
    # After 10ft setback: 25x55 interior.
    yard = _rect_polygon(width_ft=45.0, length_ft=75.0)
    result = find_largest_pool_rectangle(
        yard, min_setback_ft=5.0, house_setback_ft=10.0
    )
    short = min(result["width_ft"], result["length_ft"])
    long_ = max(result["width_ft"], result["length_ft"])
    assert short >= 15.0
    assert long_ >= 30.0


def test_ratio_clamp_rejects_pencil_pools() -> None:
    yard = _rect_polygon(width_ft=30.0, length_ft=200.0)
    result = find_largest_pool_rectangle(
        yard, min_setback_ft=5.0, house_setback_ft=10.0
    )
    short = min(result["width_ft"], result["length_ft"])
    long_ = max(result["width_ft"], result["length_ft"])
    # Width:length must be within [1:1, 1:2.5].
    if short > 0:
        assert long_ / short <= 2.5 + 1e-6


def test_lonlat_backyard_returns_lat_lon() -> None:
    # ~60x80 ft rectangle centered near Plano TX, expressed in WGS84.
    cx = -96.70
    cy = 33.02
    half_lon = (30.0 / 305_000.0)
    half_lat = (40.0 / 364_000.0)
    yard = {
        "type": "Polygon",
        "coordinates": [
            [
                [cx - half_lon, cy - half_lat],
                [cx + half_lon, cy - half_lat],
                [cx + half_lon, cy + half_lat],
                [cx - half_lon, cy + half_lat],
                [cx - half_lon, cy - half_lat],
            ]
        ],
    }
    result = find_largest_pool_rectangle(
        yard, min_setback_ft=5.0, house_setback_ft=10.0
    )
    assert result["center_lat"] is not None
    assert result["center_lon"] is not None
    # Center should sit near the polygon center.
    assert abs(result["center_lat"] - cy) < 0.001
    assert abs(result["center_lon"] - cx) < 0.001


def test_placement_rectangle_fits_within_setback() -> None:
    yard = _rect_polygon(width_ft=50.0, length_ft=80.0)
    result = find_largest_pool_rectangle(
        yard, min_setback_ft=5.0, house_setback_ft=10.0
    )
    # Pool rectangle width + length must leave at least 10ft margin.
    assert result["width_ft"] + 20.0 <= 50.0 + 1e-3 or result["width_ft"] == 0.0
    assert result["length_ft"] + 20.0 <= 80.0 + 1e-3 or result["length_ft"] == 0.0
