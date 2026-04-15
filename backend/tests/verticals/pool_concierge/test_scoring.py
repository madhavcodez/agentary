"""Unit tests for the Pool Concierge scoring bands."""

from __future__ import annotations

from app.verticals.pool_concierge.scoring import score_pool_fitness


def _dims(w: float, l: float) -> dict[str, float]:
    return {"width_ft": w, "length_ft": l}


def test_large_backyard_large_pool_scores_1_0() -> None:
    result = score_pool_fitness(
        backyard_sqft=2000.0,
        max_pool_dims=_dims(20.0, 40.0),
    )
    assert result["score"] == 1.0
    assert result["max_pool_size"] == "20x40 ft"
    assert "20x40" in result["fit_reason"]


def test_large_backyard_but_only_medium_fits_downgrades() -> None:
    result = score_pool_fitness(
        backyard_sqft=1800.0,
        max_pool_dims=_dims(15.0, 30.0),
    )
    # Big backyard but geometry only allows medium.
    assert 0.6 <= result["score"] <= 0.85
    assert result["max_pool_size"] == "15x30 ft"


def test_medium_band_gets_0_6() -> None:
    result = score_pool_fitness(
        backyard_sqft=1200.0,
        max_pool_dims=_dims(15.0, 30.0),
    )
    assert result["score"] == 0.6
    assert result["max_pool_size"] == "15x30 ft"


def test_small_backyard_gets_0() -> None:
    result = score_pool_fitness(
        backyard_sqft=800.0,
        max_pool_dims=_dims(15.0, 30.0),
    )
    assert result["score"] == 0.0
    assert result["max_pool_size"] == "does not fit"


def test_slope_over_5pct_penalizes_score() -> None:
    baseline = score_pool_fitness(
        backyard_sqft=2000.0,
        max_pool_dims=_dims(20.0, 40.0),
        slope_estimate=0.0,
    )
    steep = score_pool_fitness(
        backyard_sqft=2000.0,
        max_pool_dims=_dims(20.0, 40.0),
        slope_estimate=0.10,
    )
    assert steep["score"] < baseline["score"]
    assert steep["score"] == 0.5
    assert "Slope" in steep["fit_reason"]


def test_slope_at_threshold_does_not_penalize() -> None:
    result = score_pool_fitness(
        backyard_sqft=2000.0,
        max_pool_dims=_dims(20.0, 40.0),
        slope_estimate=0.05,
    )
    assert result["score"] == 1.0


def test_setback_violations_subtract_score() -> None:
    result = score_pool_fitness(
        backyard_sqft=2000.0,
        max_pool_dims=_dims(20.0, 40.0),
        setback_violations=2,
    )
    assert 0.65 <= result["score"] <= 0.75  # 1.0 - 0.15*2 = 0.70
    assert "setback" in result["fit_reason"].lower()


def test_only_small_pool_fits_gets_0_4() -> None:
    result = score_pool_fitness(
        backyard_sqft=1100.0,
        max_pool_dims=_dims(12.0, 24.0),
    )
    assert result["score"] == 0.4
    assert result["max_pool_size"] == "12x24 ft"


def test_zero_dims_returns_zero_score() -> None:
    result = score_pool_fitness(
        backyard_sqft=2000.0,
        max_pool_dims=_dims(0.0, 0.0),
    )
    assert result["score"] == 0.0
    assert result["max_pool_size"] == "does not fit"
