"""Unit tests for the quote ranker."""
from __future__ import annotations

import pytest

from app.services.contractors.quote_caller import QuoteResult
from app.services.contractors.quote_ranker import rank_quotes


def _quote(
    name: str,
    *,
    low: float | None,
    high: float | None,
    eta: int | None,
    rating: float | None,
    status: str = "ok",
) -> QuoteResult:
    return QuoteResult(
        contractor_name=name,
        contractor_phone=f"+1-214-555-{abs(hash(name)) % 10_000:04d}",
        status=status,  # type: ignore[arg-type]
        price_low_usd=low,
        price_high_usd=high,
        eta_weeks=eta,
        rating=rating,
    )


def test_rank_quotes_returns_top_three() -> None:
    quotes = [
        _quote("Budget", low=60_000, high=70_000, eta=8, rating=4.5),
        _quote("Premium", low=100_000, high=120_000, eta=12, rating=4.9),
        _quote("Middle", low=80_000, high=90_000, eta=10, rating=4.7),
        _quote("Slow", low=70_000, high=80_000, eta=20, rating=4.0),
    ]
    ranked = rank_quotes(quotes)
    assert len(ranked) == 3
    assert ranked[0].rank == 1
    assert ranked[1].rank == 2
    assert ranked[2].rank == 3
    # Budget — cheapest + fastest — should win.
    assert ranked[0].quote.contractor_name == "Budget"


def test_rank_quotes_weights_price_most() -> None:
    """Verify the 0.5/0.3/0.2 weights: cheap should beat fast+highly-rated."""
    cheap = _quote("Cheap", low=50_000, high=50_000, eta=15, rating=4.0)
    fancy = _quote("Fancy", low=150_000, high=150_000, eta=5, rating=5.0)
    ranked = rank_quotes([cheap, fancy])
    # price weight 0.5 * 1.0 = 0.5 for cheap
    # eta weight  0.3 * 0.0 + rating 0.2 * 0.8 = 0.16 => cheap total = 0.66
    # fancy: price 0 + eta 0.3 + rating 0.2 => 0.50
    assert ranked[0].quote.contractor_name == "Cheap"
    assert ranked[0].score == pytest.approx(0.66, abs=0.01)
    assert ranked[1].score == pytest.approx(0.50, abs=0.01)


def test_rank_quotes_drops_non_ok() -> None:
    quotes = [
        _quote("OK", low=70_000, high=80_000, eta=10, rating=4.5),
        _quote("Declined", low=None, high=None, eta=None, rating=4.5,
               status="declined"),
    ]
    ranked = rank_quotes(quotes)
    assert [r.quote.contractor_name for r in ranked] == ["OK"]


def test_rank_quotes_single_quote() -> None:
    q = _quote("Solo", low=70_000, high=80_000, eta=10, rating=4.5)
    ranked = rank_quotes([q])
    assert len(ranked) == 1
    assert ranked[0].rank == 1
    # With only one quote, inv_normalize returns 1.0 for both price & eta.
    # Score = 0.5 * 1 + 0.3 * 1 + 0.2 * 0.9 = 0.98
    assert ranked[0].score == pytest.approx(0.98, abs=1e-6)


def test_rank_quotes_empty_returns_empty() -> None:
    assert rank_quotes([]) == []


def test_rank_quotes_ignores_quotes_with_no_signals() -> None:
    quotes = [
        _quote("Signal", low=70_000, high=80_000, eta=10, rating=4.5),
        _quote("Noise", low=None, high=None, eta=None, rating=4.5),
    ]
    ranked = rank_quotes(quotes)
    assert [r.quote.contractor_name for r in ranked] == ["Signal"]


def test_rank_quotes_handles_missing_rating() -> None:
    # Rating contribution must default to 0 when missing — no KeyError.
    q = _quote("NoRating", low=70_000, high=80_000, eta=10, rating=None)
    ranked = rank_quotes([q])
    assert len(ranked) == 1
    assert ranked[0].score == pytest.approx(0.5 + 0.3 + 0.0, abs=1e-6)
