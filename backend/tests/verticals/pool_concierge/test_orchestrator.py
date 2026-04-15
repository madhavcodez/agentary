"""Unit tests for the end-to-end Pool Concierge orchestrator (Stream E).

All four pillars (mission, persist, contractor pipeline, permit list)
are injected as fakes so these run with no database and no network.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.models.contractor_report import ContractorReport
from app.models.mission import Mission
from app.models.pool_listing import PoolListing
from app.models.pool_pipeline_run import (
    PoolPipelineRun,
    PoolPipelineRunStatus,
)
from app.models.project import Project
from app.services.contractors.quote_caller import QuoteResult
from app.services.contractors.quote_ranker import RankedQuote
from app.services.permits.checklist import (
    PermitChecklist,
    PermitItem,
)
from app.verticals.pool_concierge.contractor_pipeline import (
    ContractorReportDTO,
)
from app.verticals.pool_concierge.mission import ScoredListing
from app.verticals.pool_concierge.orchestrator import (
    PoolPipelineResult,
    _get_or_create_system_project,
    _permit_specs_from_listing,
    run_full_pool_pipeline,
)


# ---------------------------------------------------------------------------
# Fake session
# ---------------------------------------------------------------------------


class FakeSession:
    """In-memory session that records every model added.

    Handles just enough SQLAlchemy surface for the orchestrator: ``add``
    flushes a fresh UUID on the model's ``id`` field, ``query`` filters
    by ``id`` on the stored objects.
    """

    def __init__(self) -> None:
        self.added: list[Any] = []
        self.flushed = 0
        self.committed = 0
        self.rolled_back = 0

    def _ensure_id(self, obj: Any) -> None:
        if hasattr(obj, "id") and obj.id is None:
            obj.id = uuid4()

    def add(self, obj: Any) -> None:
        self._ensure_id(obj)
        self.added.append(obj)

    def flush(self) -> None:
        for obj in self.added:
            self._ensure_id(obj)
        self.flushed += 1

    def commit(self) -> None:
        self.committed += 1

    def rollback(self) -> None:
        self.rolled_back += 1

    def query(self, model: type) -> "_FakeQuery":
        rows = [o for o in self.added if isinstance(o, model)]
        return _FakeQuery(rows)


class _FakeQuery:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def filter(self, *_conditions: Any) -> "_FakeQuery":
        # Our fake skips real SQL filtering — callers that rely on
        # filtering are covered by the specific tests that pre-seed the
        # session with the right object.
        return self

    def one_or_none(self) -> Any | None:
        return self._rows[0] if self._rows else None


# ---------------------------------------------------------------------------
# Fixtures / factories
# ---------------------------------------------------------------------------


def _make_scored(
    address: str, *, score: float, price: float = 850_000.0
) -> ScoredListing:
    polygon = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}
    return ScoredListing(
        listing_url=f"https://zillow.test/{address}",
        address=address,
        list_price=price,
        lot_size_sqft=12_000.0,
        building_footprint_sqft=2_200.0,
        backyard_sqft=1_500.0,
        parcel_polygon=polygon,
        backyard_polygon=polygon,
        pool_placement={"width_ft": 20.0, "length_ft": 40.0, "rotation_deg": 0.0},
        score=score,
        fit_reason="Large backyard, good placement",
        max_pool_size="20x40",
        aerial_image_url="https://mapbox.test/tile.png",
        zpid=f"z-{address[:3]}",
    )


def _fake_mission(*scored: ScoredListing):
    async def _impl(
        zipcode: str,
        radius_mi: float = 5.0,
        max_listings: int = 10,
        db: Any | None = None,
    ) -> list[ScoredListing]:
        # Sorted descending by score like the real mission does.
        return sorted(scored, key=lambda s: s.score, reverse=True)

    return _impl


def _fake_contractor(
    *,
    status: str = "ready",
    quote_count: int = 2,
) -> Any:
    calls: list[PoolListing] = []

    async def _impl(
        listing: PoolListing, db: Any, **kwargs: Any
    ) -> ContractorReportDTO:
        calls.append(listing)
        q = QuoteResult(
            contractor_name="BlueWave Pools",
            contractor_phone="+1-214-555-0101",
            status="ok",
            price_low_usd=60_000,
            price_high_usd=80_000,
            eta_weeks=8,
            rating=4.8,
        )
        top = [RankedQuote(rank=1, score=0.9, quote=q)]
        return ContractorReportDTO(
            report_id=uuid4(),
            pool_listing_id=listing.id,
            status=status,
            discovery_count=10,
            verified_count=5,
            quote_count=quote_count,
            top_quotes=top,
        )

    _impl.calls = calls  # type: ignore[attr-defined]
    return _impl


def _fake_permit(*, item_count: int = 4) -> Any:
    def _impl(jurisdiction: str, specs: Any) -> PermitChecklist:
        items = tuple(
            PermitItem(
                id=f"p{i}",
                name=f"Permit {i}",
                issuing_office="City Hall",
                est_cost_usd=100.0,
                est_processing_days=10,
                application_url="https://permit.test",
                puller="contractor_typically_pulls",
            )
            for i in range(item_count)
        )
        return PermitChecklist(
            jurisdiction=jurisdiction,
            jurisdiction_name=jurisdiction.title(),
            state="TX",
            last_verified_date="2026-04-01",
            items=items,
        )

    return _impl


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orchestrator_happy_path_completes_all_stages() -> None:
    user_id = uuid4()
    session = FakeSession()

    scored = [
        _make_scored("2025 Legacy Dr, Plano, TX 75024", score=0.93),
        _make_scored("1001 Independence Pkwy, Plano, TX 75075", score=0.81),
        _make_scored("700 Tiny Ct, Plano, TX 75023", score=0.65),
        _make_scored("404 Extra St, Plano, TX 75024", score=0.55),
    ]

    contractor = _fake_contractor(status="ready", quote_count=3)

    result: PoolPipelineResult = await run_full_pool_pipeline(
        user_id=user_id,
        zipcode="75024",
        radius_mi=5.0,
        db=session,  # type: ignore[arg-type]
        mission_fn=_fake_mission(*scored),
        contractor_fn=contractor,
        permit_fn=_fake_permit(item_count=5),
    )

    # Top-level result
    assert result.status == PoolPipelineRunStatus.ready.value
    assert result.total_listings == 4
    assert result.ready_listings == 3
    assert len(result.listings) == 3

    # Persistence: three PoolListing rows, one Mission, one Project, one
    # PoolPipelineRun all ended up on the session.
    pl_rows = [o for o in session.added if isinstance(o, PoolListing)]
    assert len(pl_rows) == 3
    assert any(isinstance(o, Mission) for o in session.added)
    assert any(isinstance(o, Project) for o in session.added)
    assert any(isinstance(o, PoolPipelineRun) for o in session.added)

    # Contractor pipeline called once per top listing.
    assert len(contractor.calls) == 3  # type: ignore[attr-defined]

    # Per-listing enrichment present in the result.
    for entry in result.listings:
        assert entry.contractor_status == "ready"
        assert entry.quote_count == 3
        assert entry.permit_item_count == 5

    assert session.committed == 1


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orchestrator_transitions_status_through_stages() -> None:
    """The run row should move through discovering -> scoring -> ready."""
    user_id = uuid4()
    session = FakeSession()
    scored = [_make_scored("1 Test Ln, Plano, TX 75024", score=0.9)]

    # Capture status after each stage via monkey-patched mission_fn.
    observed: list[str] = []

    async def _observing_mission(**kwargs: Any) -> list[ScoredListing]:
        # By now the run should have been moved to discovering.
        runs = [o for o in session.added if isinstance(o, PoolPipelineRun)]
        assert runs, "run row should be created before discovery"
        observed.append(runs[0].status.value)
        return list(scored)

    result = await run_full_pool_pipeline(
        user_id=user_id,
        zipcode="75024",
        radius_mi=5.0,
        db=session,  # type: ignore[arg-type]
        mission_fn=_observing_mission,
        contractor_fn=_fake_contractor(),
        permit_fn=_fake_permit(),
    )
    assert observed == [PoolPipelineRunStatus.discovering.value]
    assert result.status == PoolPipelineRunStatus.ready.value


@pytest.mark.asyncio
async def test_orchestrator_fails_when_mission_raises() -> None:
    session = FakeSession()

    async def _broken(**kwargs: Any) -> list[ScoredListing]:
        raise RuntimeError("mission crashed")

    result = await run_full_pool_pipeline(
        user_id=uuid4(),
        zipcode="75024",
        radius_mi=5.0,
        db=session,  # type: ignore[arg-type]
        mission_fn=_broken,
        contractor_fn=_fake_contractor(),
        permit_fn=_fake_permit(),
    )
    assert result.status == PoolPipelineRunStatus.failed.value
    assert result.listings == []


@pytest.mark.asyncio
async def test_orchestrator_fails_when_no_scored_listings() -> None:
    session = FakeSession()
    result = await run_full_pool_pipeline(
        user_id=uuid4(),
        zipcode="75024",
        radius_mi=5.0,
        db=session,  # type: ignore[arg-type]
        mission_fn=_fake_mission(),  # empty list
        contractor_fn=_fake_contractor(),
        permit_fn=_fake_permit(),
    )
    assert result.status == PoolPipelineRunStatus.failed.value
    assert result.total_listings == 0


@pytest.mark.asyncio
async def test_orchestrator_marks_failed_when_no_contractor_ready() -> None:
    session = FakeSession()
    scored = [_make_scored("1 Test Ln, Plano, TX 75024", score=0.9)]
    contractor = _fake_contractor(status="failed", quote_count=0)
    result = await run_full_pool_pipeline(
        user_id=uuid4(),
        zipcode="75024",
        radius_mi=5.0,
        db=session,  # type: ignore[arg-type]
        mission_fn=_fake_mission(*scored),
        contractor_fn=contractor,
        permit_fn=_fake_permit(),
    )
    assert result.status == PoolPipelineRunStatus.failed.value
    assert result.ready_listings == 0


# ---------------------------------------------------------------------------
# Call ordering
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orchestrator_calls_pillars_in_correct_order() -> None:
    """Mission -> persist -> contractor -> permit — in that order."""
    session = FakeSession()
    order: list[str] = []

    scored = [_make_scored("1 Order Ln, Plano, TX 75024", score=0.8)]

    async def _ordered_mission(**kwargs: Any) -> list[ScoredListing]:
        order.append("mission")
        return list(scored)

    async def _ordered_contractor(
        listing: PoolListing, db: Any, **kwargs: Any
    ) -> ContractorReportDTO:
        # Listing must have been persisted before contractor runs.
        assert listing.id is not None
        persisted = [o for o in session.added if isinstance(o, PoolListing)]
        assert listing in persisted
        order.append("contractor")
        return ContractorReportDTO(
            report_id=uuid4(),
            pool_listing_id=listing.id,
            status="ready",
            discovery_count=1,
            verified_count=1,
            quote_count=1,
            top_quotes=[],
        )

    def _ordered_permit(jurisdiction: str, specs: Any) -> PermitChecklist:
        order.append("permit")
        return PermitChecklist(
            jurisdiction=jurisdiction,
            jurisdiction_name=jurisdiction,
            state="TX",
            last_verified_date="2026-04-01",
            items=(),
        )

    await run_full_pool_pipeline(
        user_id=uuid4(),
        zipcode="75024",
        radius_mi=5.0,
        db=session,  # type: ignore[arg-type]
        mission_fn=_ordered_mission,
        contractor_fn=_ordered_contractor,
        permit_fn=_ordered_permit,
    )

    assert order == ["mission", "contractor", "permit"]


@pytest.mark.asyncio
async def test_orchestrator_honors_top_n_cap() -> None:
    session = FakeSession()
    scored = [_make_scored(f"{i} Ave", score=0.9 - i * 0.1) for i in range(5)]
    contractor = _fake_contractor()

    await run_full_pool_pipeline(
        user_id=uuid4(),
        zipcode="75024",
        radius_mi=5.0,
        db=session,  # type: ignore[arg-type]
        top_n=2,
        mission_fn=_fake_mission(*scored),
        contractor_fn=contractor,
        permit_fn=_fake_permit(),
    )
    assert len(contractor.calls) == 2  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Helper units
# ---------------------------------------------------------------------------


def test_permit_specs_map_placement_into_permit_specs() -> None:
    listing = PoolListing(
        address="1 Any Ln",
        pool_placement={"width_ft": 18.0, "length_ft": 36.0},
        backyard_sqft=1200.0,
    )
    specs = _permit_specs_from_listing(listing)
    assert specs.pool_width_ft == 18.0
    assert specs.pool_length_ft == 36.0
    assert specs.max_depth_ft == 8.0


def test_permit_specs_defaults_when_placement_is_zero() -> None:
    listing = PoolListing(
        address="1 Zero Ln",
        pool_placement={"width_ft": 0.0, "length_ft": 0.0},
        backyard_sqft=0.0,
    )
    specs = _permit_specs_from_listing(listing)
    assert specs.pool_width_ft == 15.0
    assert specs.pool_length_ft == 30.0


def test_get_or_create_system_project_is_idempotent() -> None:
    """Second call returns the same Project."""
    session = FakeSession()
    user_id = uuid4()
    first = _get_or_create_system_project(session, user_id)  # type: ignore[arg-type]
    second = _get_or_create_system_project(session, user_id)  # type: ignore[arg-type]
    # FakeSession query ignores filters, so both calls return the first
    # added project — confirming we didn't double-insert.
    assert first is second
    projects = [o for o in session.added if isinstance(o, Project)]
    assert len(projects) == 1


# ---------------------------------------------------------------------------
# Pool pipeline result serialization
# ---------------------------------------------------------------------------


def test_pool_pipeline_result_to_dict_roundtrips() -> None:
    """``to_dict`` must emit JSON-safe primitives (no UUID objects)."""
    result = PoolPipelineResult(
        run_id=uuid4(),
        user_id=uuid4(),
        zipcode="75024",
        status="ready",
        total_listings=3,
        ready_listings=3,
        listings=[],
    )
    d = result.to_dict()
    assert isinstance(d["run_id"], str)
    assert d["zipcode"] == "75024"
    assert d["listings"] == []
