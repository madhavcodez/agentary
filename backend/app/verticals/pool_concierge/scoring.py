"""Pool fitness scoring (Pool Concierge).

Deterministic bands that map (backyard_sqft, max_pool_dims, slope,
setback_violations) to a 0..1 fitness score plus a human-readable reason
and the largest fittable pool size string.
"""

from __future__ import annotations

from typing import Any


_MAX_POOL_LABELS = {
    "large": "20x40 ft",
    "medium": "15x30 ft",
    "small": "12x24 ft",
    "none": "does not fit",
}


def _pool_fits(max_pool_dims: Any, min_w: float, min_l: float) -> bool:
    """True if *max_pool_dims* indicates a pool at least min_w x min_l fits.

    Accepts any mapping with ``width_ft`` and ``length_ft`` keys or a
    2-tuple ``(width_ft, length_ft)``.
    """
    if max_pool_dims is None:
        return False
    if isinstance(max_pool_dims, dict):
        w = float(max_pool_dims.get("width_ft") or 0.0)
        l = float(max_pool_dims.get("length_ft") or 0.0)
    elif isinstance(max_pool_dims, (tuple, list)) and len(max_pool_dims) >= 2:
        w = float(max_pool_dims[0])
        l = float(max_pool_dims[1])
    else:
        return False
    short = min(w, l)
    long_ = max(w, l)
    return short >= min_w and long_ >= min_l


def score_pool_fitness(
    backyard_sqft: float,
    max_pool_dims: Any,
    slope_estimate: float = 0.0,
    setback_violations: int = 0,
) -> dict[str, Any]:
    """Return the pool fitness dict.

    Banding (pre-penalty):
        - backyard_sqft >= 1500 AND 20x40 fits -> score 1.0, "large"
        - 1000 <= backyard_sqft < 1500 AND 15x30 fits -> score 0.6, "medium"
        - backyard_sqft >= 1500 but 20x40 doesn't fit AND 15x30 does ->
          score 0.75, "medium"
        - backyard_sqft >= 1000 but only 12x24 fits -> score 0.4, "small"
        - backyard_sqft < 1000 or nothing fits -> score 0.0, "none"

    Penalties:
        - slope_estimate > 5% -> multiply score by 0.5 and amend reason
        - each setback_violation subtracts 0.15, floored at 0.0
    """
    bs = float(backyard_sqft or 0.0)
    fits_large = _pool_fits(max_pool_dims, 20.0, 40.0)
    fits_medium = _pool_fits(max_pool_dims, 15.0, 30.0)
    fits_small = _pool_fits(max_pool_dims, 12.0, 24.0)

    # Determine initial band.
    if bs >= 1500 and fits_large:
        score = 1.0
        category = "large"
        reason = (
            f"{int(bs):,} sqft backyard easily fits a 20x40 pool with "
            "setbacks."
        )
    elif bs >= 1500 and fits_medium:
        score = 0.75
        category = "medium"
        reason = (
            f"{int(bs):,} sqft backyard fits a 15x30 pool but geometry "
            "blocks a 20x40."
        )
    elif 1000 <= bs < 1500 and fits_medium:
        score = 0.6
        category = "medium"
        reason = (
            f"{int(bs):,} sqft backyard accommodates up to a 15x30 pool."
        )
    elif bs >= 1000 and fits_small:
        score = 0.4
        category = "small"
        reason = (
            f"{int(bs):,} sqft backyard only clears a 12x24 plunge pool."
        )
    else:
        score = 0.0
        category = "none"
        reason = (
            f"{int(bs):,} sqft backyard too small or shaped poorly — no "
            "standard pool fits."
        )

    # Slope penalty.
    if slope_estimate > 0.05:
        score *= 0.5
        reason += (
            f" Slope ~{slope_estimate * 100:.1f}% will add excavation cost."
        )

    # Setback violations.
    if setback_violations > 0:
        score = max(0.0, score - 0.15 * setback_violations)
        reason += (
            f" {setback_violations} setback conflict(s) flagged — verify "
            "with surveyor."
        )

    score = max(0.0, min(1.0, round(score, 3)))

    return {
        "score": float(score),
        "fit_reason": reason,
        "max_pool_size": _MAX_POOL_LABELS[category],
    }
