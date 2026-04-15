"""Rank collected voice quotes.

Pure functions — no I/O, no randomness. Score a :class:`QuoteResult`
against its cohort using inverse-normalized price and ETA plus a
normalized contractor rating. Returns the top 3.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .quote_caller import QuoteResult

_MAX_RESULTS = 3
_PRICE_WEIGHT = 0.5
_ETA_WEIGHT = 0.3
_RATING_WEIGHT = 0.2


@dataclass(frozen=True)
class RankedQuote:
    """A :class:`QuoteResult` augmented with its rank position + score."""

    rank: int
    score: float
    quote: QuoteResult

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "score": self.score,
            "quote": self.quote.to_jsonable(),
        }


def _quote_price(quote: QuoteResult) -> float | None:
    """Best-effort scalar price: midpoint when a range exists, else low."""
    if quote.price_low_usd is None and quote.price_high_usd is None:
        return None
    if quote.price_low_usd is not None and quote.price_high_usd is not None:
        return (quote.price_low_usd + quote.price_high_usd) / 2.0
    return quote.price_low_usd if quote.price_low_usd is not None else (
        quote.price_high_usd
    )


def _inv_normalize(
    value: float | None, lo: float | None, hi: float | None
) -> float:
    """Map a value in [lo, hi] to [0, 1] with *lower* = better.

    ``None`` values get ``0.0`` so a missing signal never subsidises a
    quote.
    """
    if value is None or lo is None or hi is None:
        return 0.0
    if hi <= lo:
        return 1.0
    clamped = max(min(value, hi), lo)
    return 1.0 - (clamped - lo) / (hi - lo)


def _usable(quote: QuoteResult) -> bool:
    """A quote is rankable only when we extracted at least one signal."""
    if quote.status != "ok":
        return False
    return _quote_price(quote) is not None or quote.eta_weeks is not None


def rank_quotes(quotes: list[QuoteResult]) -> list[RankedQuote]:
    """Rank quotes by composite score, return top 3.

    Score = 0.5 * inv_norm(price) + 0.3 * inv_norm(eta) + 0.2 * rating/5

    Where ``inv_norm`` maps into [0, 1] such that cheaper/faster is
    better. Quotes with status != "ok" or with no usable signals are
    filtered out.
    """
    usable = [q for q in quotes if _usable(q)]
    if not usable:
        return []

    prices = [p for p in (_quote_price(q) for q in usable) if p is not None]
    etas = [q.eta_weeks for q in usable if q.eta_weeks is not None]

    price_lo = min(prices) if prices else None
    price_hi = max(prices) if prices else None
    eta_lo = float(min(etas)) if etas else None
    eta_hi = float(max(etas)) if etas else None

    scored: list[tuple[float, QuoteResult]] = []
    for quote in usable:
        price_score = _inv_normalize(
            _quote_price(quote), price_lo, price_hi
        )
        eta_val: float | None = (
            float(quote.eta_weeks) if quote.eta_weeks is not None else None
        )
        eta_score = _inv_normalize(eta_val, eta_lo, eta_hi)
        rating_score = (
            (quote.rating / 5.0) if quote.rating is not None else 0.0
        )
        composite = (
            _PRICE_WEIGHT * price_score
            + _ETA_WEIGHT * eta_score
            + _RATING_WEIGHT * rating_score
        )
        scored.append((composite, quote))

    scored.sort(key=lambda pair: pair[0], reverse=True)

    return [
        RankedQuote(rank=idx + 1, score=round(score, 6), quote=quote)
        for idx, (score, quote) in enumerate(scored[:_MAX_RESULTS])
    ]
