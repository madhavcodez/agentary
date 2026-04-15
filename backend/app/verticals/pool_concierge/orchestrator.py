"""End-to-end Pool Concierge orchestrator (Stream E).

Wires the four pillars of the vertical into a single async entry point:

1. ``run_pool_concierge_mission`` (Stream A) — discovery + scoring
2. Persist top-3 ``ScoredListing``\\ s as :class:`PoolListing` rows
3. ``run_contractor_pipeline`` (Stream C) — voice quotes per listing
4. ``generate_permit_checklist`` (Stream D) — jurisdiction permit list

Progress is tracked on a :class:`PoolPipelineRun` row so the Telegram
bot and the API can show the user where we are (discovering, scoring,
contractor_quoting, ready).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Protocol
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from ...config import settings
from ...models.contractor_report import ContractorReport
from ...models.mission import Mission, MissionStatus, MissionType
from ...models.pool_listing import PoolListing
from ...models.pool_pipeline_run import (
    PoolPipelineRun,
    PoolPipelineRunStatus,
)
from ...models.project import Project, ProjectStatus, ProjectType
from ...services.permits.checklist import (
    PermitChecklist,
    PoolSpecs as PermitPoolSpecs,
    generate_permit_checklist,
)
from .contractor_pipeline import (
    ContractorReportDTO,
    run_contractor_pipeline,
)
from .mission import ScoredListing, run_pool_concierge_mission

logger = logging.getLogger(__name__)

_TOP_N_LISTINGS = 3
_DEFAULT_JURISDICTION = "plano_tx"
_SYSTEM_PROJECT_NAME = "Pool Concierge"


# ---------------------------------------------------------------------------
# Result DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PoolPipelineListingResult:
    """One listing's slice of the orchestrated output."""

    pool_listing_id: UUID
    address: str
    list_price: float | None
    score: float
    fit_reason: str
    max_pool_size: str
    aerial_image_url: str | None
    listing_url: str
    contractor_report_id: UUID | None
    contractor_status: str
    quote_count: int
    top_quotes: list[dict[str, Any]]
    permit_jurisdiction: str
    permit_item_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "pool_listing_id": str(self.pool_listing_id),
            "address": self.address,
            "list_price": self.list_price,
            "score": self.score,
            "fit_reason": self.fit_reason,
            "max_pool_size": self.max_pool_size,
            "aerial_image_url": self.aerial_image_url,
            "listing_url": self.listing_url,
            "contractor_report_id": (
                str(self.contractor_report_id)
                if self.contractor_report_id
                else None
            ),
            "contractor_status": self.contractor_status,
            "quote_count": self.quote_count,
            "top_quotes": list(self.top_quotes),
            "permit_jurisdiction": self.permit_jurisdiction,
            "permit_item_count": self.permit_item_count,
        }


@dataclass(frozen=True)
class PoolPipelineResult:
    """Top-level output of ``run_full_pool_pipeline``."""

    run_id: UUID
    user_id: UUID
    zipcode: str
    status: str
    total_listings: int
    ready_listings: int
    listings: list[PoolPipelineListingResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": str(self.run_id),
            "user_id": str(self.user_id),
            "zipcode": self.zipcode,
            "status": self.status,
            "total_listings": self.total_listings,
            "ready_listings": self.ready_listings,
            "listings": [l.to_dict() for l in self.listings],
        }


# ---------------------------------------------------------------------------
# Injection protocols for tests
# ---------------------------------------------------------------------------


class _MissionFn(Protocol):
    async def __call__(
        self,
        zipcode: str,
        radius_mi: float = ...,
        max_listings: int = ...,
        db: Session | None = ...,
    ) -> list[ScoredListing]: ...


class _ContractorFn(Protocol):
    async def __call__(
        self, listing: PoolListing, db: Session, **kwargs: Any
    ) -> ContractorReportDTO: ...


_PermitFn = Callable[[str, PermitPoolSpecs | None], PermitChecklist]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_or_create_system_project(db: Session, user_id: UUID) -> Project:
    """Return the user's Pool Concierge "system" project, creating if needed.

    Every ``PoolListing`` row needs a parent ``Mission`` which in turn
    needs a ``Project``. Rather than force callers to pass one in, we
    lazily create a hidden per-user Pool Concierge project.
    """
    project = (
        db.query(Project)
        .filter(
            Project.user_id == user_id,
            Project.name == _SYSTEM_PROJECT_NAME,
        )
        .one_or_none()
    )
    if project is not None:
        return project

    project = Project(
        id=uuid4(),
        user_id=user_id,
        name=_SYSTEM_PROJECT_NAME,
        description="Auto-managed Pool Concierge vertical project.",
        status=ProjectStatus.active,
        project_type=ProjectType.real_estate,
    )
    db.add(project)
    db.flush()
    return project


def _create_mission(
    db: Session, *, project_id: UUID, user_id: UUID, zipcode: str
) -> Mission:
    """Create a ``Mission`` row for this pipeline run."""
    mission = Mission(
        project_id=project_id,
        user_id=user_id,
        name=f"Pool Concierge — {zipcode}",
        description=(
            "Auto-generated mission for an end-to-end Pool Concierge run."
        ),
        objective=(
            f"Find pool-ready homes in {zipcode} and line up contractors."
        ),
        status=MissionStatus.running,
        mission_type=MissionType.data_collection,
    )
    db.add(mission)
    db.flush()
    return mission


def _persist_scored_listing(
    db: Session, *, mission_id: UUID, scored: ScoredListing
) -> PoolListing:
    """Persist one scored mission output as a ``PoolListing`` row."""
    list_price = (
        int(scored.list_price) if scored.list_price is not None else None
    )
    row = PoolListing(
        id=uuid4(),
        mission_id=mission_id,
        listing_url=scored.listing_url or None,
        address=scored.address,
        list_price=list_price,
        lot_size_sqft=scored.lot_size_sqft,
        building_footprint_sqft=scored.building_footprint_sqft,
        backyard_sqft=scored.backyard_sqft,
        parcel_polygon=scored.parcel_polygon,
        backyard_polygon=scored.backyard_polygon,
        pool_placement=scored.pool_placement,
        score=scored.score,
        fit_reason=scored.fit_reason,
        max_pool_size=scored.max_pool_size,
        aerial_image_url=scored.aerial_image_url,
    )
    db.add(row)
    db.flush()
    return row


def _update_run(
    db: Session,
    run: PoolPipelineRun,
    *,
    status: PoolPipelineRunStatus | None = None,
    total_listings: int | None = None,
    ready_listings: int | None = None,
    summary: dict[str, Any] | None = None,
    completed: bool = False,
) -> None:
    """Patch a run row in place. Flushes but does not commit."""
    if status is not None:
        run.status = status
    if total_listings is not None:
        run.total_listings = total_listings
    if ready_listings is not None:
        run.ready_listings = ready_listings
    if summary is not None:
        run.summary = summary
    if completed:
        run.completed_at = datetime.now(timezone.utc)
    db.flush()


def _permit_specs_from_listing(listing: PoolListing) -> PermitPoolSpecs:
    """Map a ``PoolListing``'s placement into ``PermitPoolSpecs`` shape."""
    placement = listing.pool_placement or {}
    length_ft = float(placement.get("length_ft") or 30.0)
    width_ft = float(placement.get("width_ft") or 15.0)
    # Guard against zero-sized placements returned by degenerate mocks.
    if length_ft <= 0.0:
        length_ft = 30.0
    if width_ft <= 0.0:
        width_ft = 15.0
    return PermitPoolSpecs(
        pool_length_ft=length_ft,
        pool_width_ft=width_ft,
        max_depth_ft=8.0,
        has_spa=False,
        includes_fence_construction=False,
        hoa_applies=False,
    )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


async def run_full_pool_pipeline(
    user_id: UUID,
    zipcode: str,
    radius_mi: float,
    db: Session,
    *,
    max_listings: int = 10,
    top_n: int = _TOP_N_LISTINGS,
    jurisdiction: str = _DEFAULT_JURISDICTION,
    mission_fn: _MissionFn | None = None,
    contractor_fn: _ContractorFn | None = None,
    permit_fn: _PermitFn | None = None,
    run_id: UUID | None = None,
    commit: bool = True,
) -> PoolPipelineResult:
    """Run discovery, scoring, contractor pipeline, and permits end-to-end.

    Args:
        user_id: Owning user (required for FK on :class:`PoolPipelineRun`
            and the hidden system project).
        zipcode: Target US 5-digit ZIP (e.g. ``"75024"``).
        radius_mi: Search radius passed to the mission.
        db: SQLAlchemy session. The orchestrator creates a
            ``PoolPipelineRun`` early so callers can poll progress even
            mid-run.
        max_listings: Upper bound on scored mission output (Stream A).
        top_n: Number of top-ranked listings to run contractor + permit
            pipelines for. Default ``3``.
        jurisdiction: Permit checklist slug.
        mission_fn / contractor_fn / permit_fn: DI hooks for tests.
        run_id: Optional caller-provided run id (used by the API layer
            that pre-creates the row before returning 202).
        commit: When False, only flushes (lets a caller wrap multiple
            calls in a single transaction).

    Returns:
        :class:`PoolPipelineResult` — status, per-listing details,
        and counts.
    """
    if not settings.pool_concierge_enabled:
        logger.warning(
            "Pool Concierge disabled via settings — running anyway for "
            "user %s because a caller explicitly invoked the pipeline.",
            user_id,
        )

    mission = mission_fn or run_pool_concierge_mission
    contractor = contractor_fn or run_contractor_pipeline
    permit = permit_fn or (
        lambda j, s: generate_permit_checklist(jurisdiction=j, pool_specs=s)
    )

    # Pre-create or load the run row so the API can return a run_id
    # immediately. Caller may have already inserted one — honor it.
    run = _load_or_create_run(db, user_id=user_id, zipcode=zipcode, run_id=run_id)
    _update_run(db, run, status=PoolPipelineRunStatus.discovering)

    try:
        scored = await mission(
            zipcode=zipcode,
            radius_mi=radius_mi,
            max_listings=max_listings,
            db=db,
        )
    except Exception:
        logger.exception(
            "Pool Concierge mission failed for user %s / ZIP %s",
            user_id,
            zipcode,
        )
        _update_run(
            db,
            run,
            status=PoolPipelineRunStatus.failed,
            completed=True,
        )
        if commit:
            db.commit()
        return _result_from_run(run, listings=[])

    _update_run(
        db,
        run,
        status=PoolPipelineRunStatus.scoring,
        total_listings=len(scored),
    )

    if not scored:
        _update_run(
            db,
            run,
            status=PoolPipelineRunStatus.failed,
            completed=True,
        )
        if commit:
            db.commit()
        return _result_from_run(run, listings=[])

    top_scored = scored[:top_n]

    # Stage 2: persist PoolListing rows (needs a Mission FK).
    project = _get_or_create_system_project(db, user_id)
    mission_row = _create_mission(
        db, project_id=project.id, user_id=user_id, zipcode=zipcode
    )
    persisted: list[tuple[PoolListing, ScoredListing]] = []
    for s in top_scored:
        pl = _persist_scored_listing(
            db, mission_id=mission_row.id, scored=s
        )
        persisted.append((pl, s))

    _update_run(db, run, status=PoolPipelineRunStatus.contractor_quoting)

    # Stage 3 + 4: contractor quotes and permit checklists per listing.
    listing_results: list[PoolPipelineListingResult] = []
    for pl, s in persisted:
        listing_results.append(
            await _run_per_listing_stages(
                db=db,
                listing=pl,
                scored=s,
                contractor_fn=contractor,
                permit_fn=permit,
                jurisdiction=jurisdiction,
            )
        )

    ready_count = sum(
        1 for lr in listing_results if lr.contractor_status == "ready"
    )
    final_status = (
        PoolPipelineRunStatus.ready
        if ready_count > 0
        else PoolPipelineRunStatus.failed
    )

    summary = {
        "top_listings": [lr.to_dict() for lr in listing_results],
        "jurisdiction": jurisdiction,
    }
    _update_run(
        db,
        run,
        status=final_status,
        total_listings=len(scored),
        ready_listings=ready_count,
        summary=summary,
        completed=True,
    )

    mission_row.status = MissionStatus.completed
    mission_row.completed_at = datetime.now(timezone.utc)
    db.flush()

    if commit:
        db.commit()

    return _result_from_run(run, listings=listing_results)


async def _run_per_listing_stages(
    *,
    db: Session,
    listing: PoolListing,
    scored: ScoredListing,
    contractor_fn: _ContractorFn,
    permit_fn: _PermitFn,
    jurisdiction: str,
) -> PoolPipelineListingResult:
    """Execute contractor-pipeline + permit-checklist for one listing."""
    contractor_report_id: UUID | None = None
    contractor_status = "skipped"
    quote_count = 0
    top_quotes: list[dict[str, Any]] = []

    try:
        report: ContractorReportDTO = await contractor_fn(
            listing=listing, db=db, commit=False
        )
        contractor_report_id = report.report_id
        contractor_status = report.status
        quote_count = report.quote_count
        top_quotes = [rq.to_jsonable() for rq in report.top_quotes]
    except Exception:
        logger.exception(
            "Contractor pipeline failed for listing %s", listing.id
        )
        contractor_status = "failed"

    permit_item_count = 0
    try:
        checklist = permit_fn(
            jurisdiction, _permit_specs_from_listing(listing)
        )
        permit_item_count = len(checklist.items)
    except Exception:
        logger.exception(
            "Permit checklist failed for listing %s", listing.id
        )

    return PoolPipelineListingResult(
        pool_listing_id=listing.id,
        address=listing.address,
        list_price=(
            float(listing.list_price)
            if listing.list_price is not None
            else None
        ),
        score=float(listing.score or 0.0),
        fit_reason=listing.fit_reason or "",
        max_pool_size=listing.max_pool_size or "",
        aerial_image_url=listing.aerial_image_url,
        listing_url=listing.listing_url or scored.listing_url or "",
        contractor_report_id=contractor_report_id,
        contractor_status=contractor_status,
        quote_count=quote_count,
        top_quotes=top_quotes,
        permit_jurisdiction=jurisdiction,
        permit_item_count=permit_item_count,
    )


def _load_or_create_run(
    db: Session,
    *,
    user_id: UUID,
    zipcode: str,
    run_id: UUID | None,
) -> PoolPipelineRun:
    """Load a pre-seeded run row (if ``run_id`` was supplied) or make one."""
    if run_id is not None:
        existing = (
            db.query(PoolPipelineRun)
            .filter(PoolPipelineRun.id == run_id)
            .one_or_none()
        )
        if existing is not None:
            return existing

    run = PoolPipelineRun(
        id=run_id or uuid4(),
        user_id=user_id,
        zipcode=zipcode,
        status=PoolPipelineRunStatus.pending,
        total_listings=0,
        ready_listings=0,
    )
    db.add(run)
    db.flush()
    return run


def _result_from_run(
    run: PoolPipelineRun,
    *,
    listings: list[PoolPipelineListingResult],
) -> PoolPipelineResult:
    return PoolPipelineResult(
        run_id=run.id,
        user_id=run.user_id,
        zipcode=run.zipcode,
        status=run.status.value,
        total_listings=int(run.total_listings or 0),
        ready_listings=int(run.ready_listings or 0),
        listings=listings,
    )
