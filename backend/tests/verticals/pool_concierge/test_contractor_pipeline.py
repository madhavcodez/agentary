"""End-to-end contractor pipeline test with all external services mocked."""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.models.contractor_report import (
    ContractorReport,
    ContractorReportStatus,
)
from app.services.contractors.discovery import ContractorCandidate
from app.services.contractors.license_verifier import LicenseStatus
from app.services.contractors.quote_caller import PoolSpecs, QuoteResult
from app.verticals.pool_concierge.contractor_pipeline import (
    _extract_city,
    _extract_state,
    _extract_zip,
    run_contractor_pipeline,
)


# ---------------------------------------------------------------------------
# Address parser unit tests
# ---------------------------------------------------------------------------


def test_extract_zip_ok() -> None:
    assert _extract_zip("123 Yard Ln, Plano, TX 75023") == "75023"


def test_extract_zip_handles_zip_plus_four() -> None:
    assert _extract_zip("1 St, Plano, TX 75023-1234") == "75023"


def test_extract_zip_none_when_absent() -> None:
    assert _extract_zip(None) is None
    assert _extract_zip("no address") is None


def test_extract_state_reads_two_letter_code() -> None:
    assert _extract_state("1 St, Plano, TX 75023") == "TX"
    assert _extract_state("1 St, Los Angeles, CA 90001") == "CA"


def test_extract_state_defaults_to_tx() -> None:
    assert _extract_state(None) == "TX"


def test_extract_city() -> None:
    assert _extract_city("1 St, Plano, TX 75023") == "Plano"
    assert _extract_city(None) is None


# ---------------------------------------------------------------------------
# run_contractor_pipeline happy path (everything stubbed)
# ---------------------------------------------------------------------------


class _FakeListing:
    def __init__(
        self,
        address: str = "123 Yard Lane, Plano, TX 75023",
        placement: dict[str, Any] | None = None,
        backyard_sqft: float = 1200.0,
    ) -> None:
        self.id = uuid4()
        self.address = address
        self.pool_placement = placement or {
            "width_ft": 20.0,
            "length_ft": 40.0,
            "rotation_deg": 0.0,
        }
        self.backyard_sqft = backyard_sqft


class _FakeSession:
    """Just enough SQLAlchemy-session surface for the pipeline."""

    def __init__(self) -> None:
        self.added: list[Any] = []
        self.flushed = 0
        self.committed = 0
        self.rolled_back = 0

    def add(self, obj: Any) -> None:
        # Assign a UUID on first add so ContractorReport has an id.
        if isinstance(obj, ContractorReport) and obj.id is None:
            obj.id = uuid4()
        self.added.append(obj)

    def flush(self) -> None:
        for obj in self.added:
            if isinstance(obj, ContractorReport) and obj.id is None:
                obj.id = uuid4()
        self.flushed += 1

    def commit(self) -> None:
        self.committed += 1

    def rollback(self) -> None:
        self.rolled_back += 1


def _fake_discover(*candidates: ContractorCandidate):
    async def _impl(
        zipcode: str,
        radius_mi: float = 15.0,
        min_rating: float = 4.0,
        min_reviews: int = 20,
        limit: int = 10,
    ) -> list[ContractorCandidate]:
        return list(candidates)

    return _impl


def _fake_verify(*, only_found: set[str] | None = None):
    async def _impl(
        state: str, business_name: str, city: str | None = None
    ) -> LicenseStatus:
        if only_found is None or business_name in only_found:
            return LicenseStatus(
                found=True,
                license_number=f"APS-{hash(business_name) & 0xffff:04x}",
                status="Active",
            )
        return LicenseStatus(found=False, status="no_records")

    return _impl


def _fake_quote(quote_by_name: dict[str, QuoteResult]):
    async def _impl(
        contractor: ContractorCandidate,
        listing: Any,
        pool_specs: PoolSpecs,
        max_call_duration_sec: int = 240,
    ) -> QuoteResult:
        return quote_by_name[contractor.name]

    return _impl


@pytest.mark.asyncio
async def test_pipeline_happy_path_produces_top_quotes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    listing = _FakeListing()
    session = _FakeSession()

    candidates = [
        ContractorCandidate(
            name="BlueWave Pools",
            phone="+1-214-555-0101",
            address="",
            rating=4.8,
            reviews_count=200,
            source="yelp",
            business_url="",
            raw_payload={},
        ),
        ContractorCandidate(
            name="Sunset Pools",
            phone="+1-214-555-0102",
            address="",
            rating=4.5,
            reviews_count=80,
            source="yelp",
            business_url="",
            raw_payload={},
        ),
        ContractorCandidate(
            name="Reef Pools",
            phone="+1-214-555-0103",
            address="",
            rating=4.7,
            reviews_count=140,
            source="google_places",
            business_url="",
            raw_payload={},
        ),
        ContractorCandidate(
            name="Ghost Pools",  # will fail license verification
            phone="+1-214-555-0104",
            address="",
            rating=4.9,
            reviews_count=40,
            source="google_places",
            business_url="",
            raw_payload={},
        ),
    ]

    quotes = {
        "BlueWave Pools": QuoteResult(
            contractor_name="BlueWave Pools",
            contractor_phone="+1-214-555-0101",
            status="ok",
            price_low_usd=60_000,
            price_high_usd=80_000,
            eta_weeks=8,
            rating=4.8,
        ),
        "Sunset Pools": QuoteResult(
            contractor_name="Sunset Pools",
            contractor_phone="+1-214-555-0102",
            status="ok",
            price_low_usd=100_000,
            price_high_usd=120_000,
            eta_weeks=14,
            rating=4.5,
        ),
        "Reef Pools": QuoteResult(
            contractor_name="Reef Pools",
            contractor_phone="+1-214-555-0103",
            status="ok",
            price_low_usd=75_000,
            price_high_usd=90_000,
            eta_weeks=10,
            rating=4.7,
        ),
    }

    dto = await run_contractor_pipeline(
        listing=listing,  # type: ignore[arg-type]
        db=session,  # type: ignore[arg-type]
        discover_fn=_fake_discover(*candidates),
        verify_fn=_fake_verify(
            only_found={"BlueWave Pools", "Sunset Pools", "Reef Pools"}
        ),
        quote_fn=_fake_quote(quotes),
    )

    assert dto.status == ContractorReportStatus.ready.value
    assert dto.discovery_count == 4
    assert dto.verified_count == 3
    assert dto.quote_count == 3
    assert len(dto.top_quotes) == 3

    # Cheapest+fastest should be first.
    names = [rq.quote.contractor_name for rq in dto.top_quotes]
    assert names[0] == "BlueWave Pools"
    assert set(names) == {"BlueWave Pools", "Reef Pools", "Sunset Pools"}

    # Persistence: ContractorReport row was added to the session.
    assert any(isinstance(o, ContractorReport) for o in session.added)
    assert session.committed == 1


@pytest.mark.asyncio
async def test_pipeline_marks_failed_when_no_quotes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    listing = _FakeListing()
    session = _FakeSession()

    dto = await run_contractor_pipeline(
        listing=listing,  # type: ignore[arg-type]
        db=session,  # type: ignore[arg-type]
        discover_fn=_fake_discover(),  # no candidates
        verify_fn=_fake_verify(),
        quote_fn=_fake_quote({}),
    )
    assert dto.status == ContractorReportStatus.failed.value
    assert dto.discovery_count == 0
    assert dto.verified_count == 0
    assert dto.quote_count == 0
    assert dto.top_quotes == []


@pytest.mark.asyncio
async def test_pipeline_no_zip_fails_cleanly() -> None:
    listing = _FakeListing(address="No ZIP anywhere")
    session = _FakeSession()

    async def _should_not_be_called(*a: Any, **kw: Any) -> Any:
        raise AssertionError("discover should not be called")

    dto = await run_contractor_pipeline(
        listing=listing,  # type: ignore[arg-type]
        db=session,  # type: ignore[arg-type]
        discover_fn=_should_not_be_called,
        verify_fn=_fake_verify(),
        quote_fn=_fake_quote({}),
    )
    assert dto.status == ContractorReportStatus.failed.value
    assert dto.discovery_count == 0


@pytest.mark.asyncio
async def test_pipeline_integrates_with_pool_listing_attributes() -> None:
    """Sanity: the pipeline reads ``address`` + ``pool_placement`` + ``backyard_sqft``
    off the PoolListing model surface defined by Stream A."""
    from app.models.pool_listing import PoolListing as StreamAPoolListing

    # Verify the fields we rely on exist on the real model.
    for field in ("address", "pool_placement", "backyard_sqft", "id"):
        assert hasattr(StreamAPoolListing, field), (
            f"Stream A PoolListing should expose {field}"
        )
