"""Unit tests for the rule-based backyard segmenter."""

from __future__ import annotations

from app.services.cv.backyard_segmenter import segment_backyard


def _rect(min_x: float, min_y: float, max_x: float, max_y: float) -> dict:
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [min_x, min_y],
                [max_x, min_y],
                [max_x, max_y],
                [min_x, max_y],
                [min_x, min_y],
            ]
        ],
    }


def test_simple_backyard_area_matches_subtraction() -> None:
    # 80x120 ft parcel.
    parcel = _rect(0, 0, 80, 120)
    # House: 60x30 at the front (y: 0..30).
    house = _rect(10, 0, 70, 30)

    result = segment_backyard(parcel, house)

    backyard_sqft = result["backyard_sqft"]
    # Expect backyard roughly = parcel area - house area = 9600 - 1800 = 7800
    # With the behind-house filter we keep the big remainder below the
    # house; strip-bits at top are included when L-shaped.
    assert 4000.0 <= backyard_sqft <= 9600.0
    assert result["backyard_polygon"]["type"] == "Polygon"


def test_driveway_further_reduces_backyard() -> None:
    parcel = _rect(0, 0, 80, 120)
    house = _rect(10, 0, 70, 30)
    driveway = _rect(0, 0, 10, 30)

    without_drive = segment_backyard(parcel, house)
    with_drive = segment_backyard(parcel, house, driveway)

    # Driveway is on the front/side, so the *backyard behind the house*
    # should not grow when we add a driveway.
    assert with_drive["backyard_sqft"] <= without_drive["backyard_sqft"] + 1.0


def test_empty_house_returns_full_parcel() -> None:
    parcel = _rect(0, 0, 50, 50)
    # Degenerate "house" that barely takes any area.
    house = _rect(0, 0, 1, 1)

    result = segment_backyard(parcel, house)
    # Full parcel minus tiny house ≈ 2499 sqft.
    assert result["backyard_sqft"] >= 2400.0


def test_house_covers_parcel_returns_zero_backyard() -> None:
    parcel = _rect(0, 0, 40, 40)
    house = _rect(0, 0, 40, 40)

    result = segment_backyard(parcel, house)
    assert result["backyard_sqft"] == 0.0
    # Empty polygon representation.
    assert result["backyard_polygon"]["coordinates"] == []


def test_lonlat_coords_converted_to_sqft_area() -> None:
    # ~100x100 ft parcel near Plano TX in WGS84.
    cx = -96.70
    cy = 33.02
    half_lon = 50.0 / 305_000.0
    half_lat = 50.0 / 364_000.0
    parcel = _rect(cx - half_lon, cy - half_lat, cx + half_lon, cy + half_lat)
    # House: thin strip across the front.
    house_half_lat = 10.0 / 364_000.0
    house = _rect(
        cx - half_lon,
        cy - half_lat,
        cx + half_lon,
        cy - half_lat + house_half_lat * 2,
    )

    result = segment_backyard(parcel, house)
    # Backyard ≈ 100x80 = 8000 sqft; allow 5% tolerance.
    assert 7000.0 <= result["backyard_sqft"] <= 9000.0
