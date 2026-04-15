"""FastAPI router for the end-to-end Pool Concierge orchestrator (Stream E).

Endpoints
---------
* ``POST /api/verticals/pool/run`` — kick off a full pipeline run for a
  user. Returns 202 plus the ``run_id`` immediately. The pipeline
  continues in a FastAPI ``BackgroundTask``.
* ``GET /api/verticals/pool/runs/{run_id}`` — read the current state of
  a :class:`PoolPipelineRun` (status, counts, serialized summary).
* ``POST /api/verticals/pool/runs/{run_id}/notify-telegram`` — send the
  digest for this run to the user's Telegram chat.

Wire into ``app/main.py`` with::

    from .api.verticals.pool_orchestrator import router as pool_orchestrator_router
    app.include_router(pool_orchestrator_router)
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from ...database import SessionLocal
from ...deps import get_current_user, get_db
from ...models.pool_pipeline_run import (
    PoolPipelineRun,
    PoolPipelineRunStatus,
)
from ...models.user import User
from ...services.telegram.pool_handlers import (
    build_digest_buttons,
    render_digest,
)
from ...services.telegram.telegram_client import TelegramClient
from ...verticals.pool_concierge.orchestrator import run_full_pool_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/verticals/pool", tags=["pool-concierge"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class RunPipelineRequest(_Frozen):
    """Kickoff body for ``POST /api/verticals/pool/run``."""

    user_id: UUID
    zipcode: str = Field(min_length=5, max_length=10)
    radius_mi: float = Field(default=5.0, gt=0.0, le=50.0)


class RunPipelineResponse(_Frozen):
    """Response envelope for the kickoff endpoint."""

    run_id: UUID
    status: str
    message: str


class PipelineRunView(_Frozen):
    """Serialized ``PoolPipelineRun`` row for ``GET`` endpoint."""

    run_id: UUID
    user_id: UUID
    zipcode: str
    status: str
    total_listings: int
    ready_listings: int
    telegram_message_id: str | None
    summary: dict[str, Any] | None
    created_at: str | None
    completed_at: str | None


class NotifyTelegramRequest(_Frozen):
    """Body for the Telegram notify endpoint."""

    chat_id: str = Field(min_length=1, max_length=64)


class NotifyTelegramResponse(_Frozen):
    """Result of the Telegram digest send."""

    run_id: UUID
    delivered: bool
    message_id: str | None


# ---------------------------------------------------------------------------
# Background runner
# ---------------------------------------------------------------------------


async def _run_pipeline_async(
    user_id: UUID,
    zipcode: str,
    radius_mi: float,
    run_id: UUID,
) -> None:
    """Async pipeline runner for FastAPI ``BackgroundTasks``.

    FastAPI awaits async callables added via ``background_tasks.add_task``
    so we stay on the running uvicorn loop — calling ``asyncio.run``
    here would raise ``RuntimeError: This event loop is already
    running`` (see Stream C's audit fix on ``pool_contractors``).

    Opens its OWN ``SessionLocal()`` — the request-scoped session closes
    when the request ends, long before the background task runs.
    """
    session = SessionLocal()
    try:
        try:
            await run_full_pool_pipeline(
                user_id=user_id,
                zipcode=zipcode,
                radius_mi=radius_mi,
                db=session,
                run_id=run_id,
            )
        except Exception:
            logger.exception(
                "Pool pipeline background run failed for run_id=%s",
                run_id,
            )
            _mark_failed(session, run_id)
    finally:
        session.close()


def _mark_failed(db: Session, run_id: UUID) -> None:
    """Best-effort fail-the-run on an unexpected crash."""
    try:
        run = (
            db.query(PoolPipelineRun)
            .filter(PoolPipelineRun.id == run_id)
            .one_or_none()
        )
        if run is not None:
            run.status = PoolPipelineRunStatus.failed
            db.commit()
    except Exception:  # pragma: no cover — best-effort cleanup
        logger.exception("Failed to mark run %s as failed", run_id)
        db.rollback()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/run",
    response_model=RunPipelineResponse,
    status_code=202,
)
def run_pipeline(
    payload: RunPipelineRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> RunPipelineResponse:
    """Enqueue an end-to-end Pool Concierge pipeline run."""
    user = (
        db.query(User)
        .filter(User.id == payload.user_id)
        .one_or_none()
    )
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")

    run_id = uuid4()
    run = PoolPipelineRun(
        id=run_id,
        user_id=payload.user_id,
        zipcode=payload.zipcode,
        status=PoolPipelineRunStatus.pending,
        total_listings=0,
        ready_listings=0,
    )
    db.add(run)
    db.commit()

    background_tasks.add_task(
        _run_pipeline_async,
        payload.user_id,
        payload.zipcode,
        payload.radius_mi,
        run_id,
    )

    return RunPipelineResponse(
        run_id=run_id,
        status=run.status.value,
        message="pool pipeline queued",
    )


@router.get(
    "/runs/{run_id}",
    response_model=PipelineRunView,
)
def get_run(
    run_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> PipelineRunView:
    """Fetch a single pipeline run row."""
    run = (
        db.query(PoolPipelineRun)
        .filter(PoolPipelineRun.id == run_id)
        .one_or_none()
    )
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return _run_to_view(run)


@router.post(
    "/runs/{run_id}/notify-telegram",
    response_model=NotifyTelegramResponse,
)
async def notify_telegram(
    run_id: UUID,
    payload: NotifyTelegramRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> NotifyTelegramResponse:
    """Send the Pool Concierge digest for ``run_id`` to a Telegram chat."""
    run = (
        db.query(PoolPipelineRun)
        .filter(PoolPipelineRun.id == run_id)
        .one_or_none()
    )
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")

    view = _run_to_view(run)
    body = render_digest(view.model_dump())
    buttons = build_digest_buttons(view.model_dump())

    client = TelegramClient()
    try:
        if buttons:
            result = await client.send_message_with_buttons(
                payload.chat_id, body, buttons
            )
        else:
            result = await client.send_message(payload.chat_id, body)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Telegram send failed for run %s", run_id)
        raise HTTPException(
            status_code=502, detail=f"telegram send failed: {exc}"
        ) from exc

    if result.ok and result.message_id:
        run.telegram_message_id = result.message_id
        db.commit()

    return NotifyTelegramResponse(
        run_id=run_id,
        delivered=result.ok,
        message_id=result.message_id,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_to_view(run: PoolPipelineRun) -> PipelineRunView:
    return PipelineRunView(
        run_id=run.id,
        user_id=run.user_id,
        zipcode=run.zipcode,
        status=run.status.value,
        total_listings=int(run.total_listings or 0),
        ready_listings=int(run.ready_listings or 0),
        telegram_message_id=run.telegram_message_id,
        summary=dict(run.summary) if run.summary else None,
        created_at=(run.created_at.isoformat() if run.created_at else None),
        completed_at=(
            run.completed_at.isoformat() if run.completed_at else None
        ),
    )
