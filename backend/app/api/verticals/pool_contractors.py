"""FastAPI router for contractor-pipeline endpoints (Stream C).

Endpoints
---------
POST /api/verticals/pool/listings/{listing_id}/contractors
    Kick off the contractor pipeline for a PoolListing. Returns 202
    with the report_id — the pipeline runs as a FastAPI BackgroundTask
    so the HTTP call returns immediately.

GET /api/verticals/pool/contractors/{report_id}
    Return a ContractorReport row as JSON, including the ranked
    top-quotes payload.

Wire into ``app/main.py`` with::

    from .api.verticals.pool_contractors import router as pool_contractors_router
    app.include_router(pool_contractors_router)
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from ...database import SessionLocal
from ...deps import get_current_user, get_db
from ...models.contractor_report import (
    ContractorReport,
    ContractorReportStatus,
)
from ...models.pool_listing import PoolListing
from ...models.user import User
from ...verticals.pool_concierge.contractor_pipeline import (
    run_contractor_pipeline,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/verticals/pool", tags=["pool-concierge"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ContractorKickoffRequest(_Frozen):
    # Security audit #6: zipcode is accepted here only as an OPTIONAL
    # override. When omitted, the pipeline pulls the ZIP from the
    # PoolListing. The pydantic ``pattern`` enforces a 5-digit US ZIP
    # (optionally +4) so a malicious request cannot smuggle arbitrary
    # strings into downstream connectors.
    zipcode: str | None = Field(default=None, pattern=r"^\d{5}(-\d{4})?$")
    radius_mi: float = Field(default=15.0, gt=0.0, le=50.0)
    min_rating: float = Field(default=4.0, ge=0.0, le=5.0)
    min_reviews: int = Field(default=20, ge=0)
    discovery_limit: int = Field(default=10, gt=0, le=25)


class ContractorKickoffResponse(_Frozen):
    report_id: UUID
    status: str
    message: str


class ContractorReportView(_Frozen):
    report_id: UUID
    pool_listing_id: UUID
    status: str
    discovery_count: int
    verified_count: int
    quote_count: int
    top_quotes: list[dict[str, Any]]
    created_at: str
    completed_at: str | None


# ---------------------------------------------------------------------------
# Background runner
# ---------------------------------------------------------------------------


async def _run_pipeline_async(
    listing_id: UUID,
    report_id: UUID,
    radius_mi: float,
    min_rating: float,
    min_reviews: int,
    discovery_limit: int,
) -> None:
    """Async pipeline runner used by FastAPI ``BackgroundTasks``.

    Audit fixes:
      * code-review CRITICAL #1 — Previously ``asyncio.run(...)`` inside a
        BackgroundTask executed on the already-running uvicorn event
        loop, raising ``RuntimeError: This event loop is already
        running`` on every call. FastAPI natively awaits async callables
        added via ``background_tasks.add_task`` so we can simply be an
        ``async def`` coroutine.
      * code-review HIGH #6 — The endpoint now creates the
        ``ContractorReport`` row and passes ``report_id`` in; we forward
        it via ``existing_report_id=`` so the pipeline reuses the row
        instead of creating a second one.

    Opens its OWN ``SessionLocal()`` — the request-scoped session closes
    when the request ends, long before the background task runs.
    """
    session = SessionLocal()
    try:
        listing = (
            session.query(PoolListing)
            .filter(PoolListing.id == listing_id)
            .one_or_none()
        )
        if listing is None:
            logger.error(
                "Background contractor pipeline: listing %s missing", listing_id
            )
            _mark_failed(session, report_id)
            return
        try:
            await run_contractor_pipeline(
                listing=listing,
                db=session,
                radius_mi=radius_mi,
                min_rating=min_rating,
                min_reviews=min_reviews,
                discovery_limit=discovery_limit,
                existing_report_id=report_id,
            )
        except Exception:
            logger.exception(
                "Background contractor pipeline failed for listing %s",
                listing_id,
            )
            _mark_failed(session, report_id)
    finally:
        session.close()


def _mark_failed(db: Session, report_id: UUID) -> None:
    """Best-effort mark a report row as failed after a crash."""
    try:
        report = (
            db.query(ContractorReport)
            .filter(ContractorReport.id == report_id)
            .one_or_none()
        )
        if report is not None:
            report.status = ContractorReportStatus.failed
            db.commit()
    except Exception:  # pragma: no cover — best-effort cleanup
        logger.exception("Failed to mark report %s as failed", report_id)
        db.rollback()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/listings/{listing_id}/contractors",
    response_model=ContractorKickoffResponse,
    status_code=202,
)
def kickoff_contractor_pipeline(
    listing_id: UUID,
    payload: ContractorKickoffRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> ContractorKickoffResponse:
    """Start the contractor pipeline for a PoolListing."""
    listing = (
        db.query(PoolListing)
        .filter(PoolListing.id == listing_id)
        .one_or_none()
    )
    if listing is None:
        raise HTTPException(status_code=404, detail="pool listing not found")

    report = ContractorReport(
        pool_listing_id=listing_id,
        status=ContractorReportStatus.pending,
        discovery_count=0,
        verified_count=0,
        quote_count=0,
        top_quotes=[],
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    background_tasks.add_task(
        _run_pipeline_async,
        listing_id,
        report.id,
        payload.radius_mi,
        payload.min_rating,
        payload.min_reviews,
        payload.discovery_limit,
    )

    return ContractorKickoffResponse(
        report_id=report.id,
        status=report.status.value,
        message="contractor pipeline queued",
    )


@router.get(
    "/contractors/{report_id}",
    response_model=ContractorReportView,
)
def get_contractor_report(
    report_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> ContractorReportView:
    """Return a ContractorReport row."""
    report = (
        db.query(ContractorReport)
        .filter(ContractorReport.id == report_id)
        .one_or_none()
    )
    if report is None:
        raise HTTPException(status_code=404, detail="report not found")

    return ContractorReportView(
        report_id=report.id,
        pool_listing_id=report.pool_listing_id,
        status=report.status.value,
        discovery_count=int(report.discovery_count or 0),
        verified_count=int(report.verified_count or 0),
        quote_count=int(report.quote_count or 0),
        top_quotes=list(report.top_quotes or []),
        created_at=(
            report.created_at.isoformat() if report.created_at else ""
        ),
        completed_at=(
            report.completed_at.isoformat() if report.completed_at else None
        ),
    )
