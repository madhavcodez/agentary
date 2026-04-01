"""Celery tasks for crew execution."""
from __future__ import annotations

import asyncio
import logging
import uuid

from ..celery_app import celery_app
from ..core.correlation import correlation_id_var
from ..database import SessionLocal
from ..models.enums import RunStatus
from ..services.crews.crew_runner import CrewRunner
from ..services.crews.crew_service import assemble_crew, start_crew_run
from ..models.mission import Mission, MissionStatus
from ..models.mission_run import MissionRun
from ..models.crew_run import CrewRun

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine in a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _is_already_completed(db, model_class, record_id: uuid.UUID) -> bool:
    """Check if a run record is already in a terminal state (idempotency guard)."""
    record = db.query(model_class).filter_by(id=record_id).first()
    if not record:
        return False
    status_val = record.status.value if hasattr(record.status, "value") else str(record.status)
    return status_val in ("completed", "failed", "cancelled")


@celery_app.task(
    name="crew.execute_run",
    queue="missions",
    bind=True,
    max_retries=2,
    soft_time_limit=3600,
    time_limit=3900,
)
def execute_crew_run(self, run_id: str, correlation_id: str | None = None) -> dict:
    """Execute a crew run in the background."""
    if correlation_id:
        correlation_id_var.set(correlation_id)

    db = SessionLocal()
    try:
        # Idempotency check — skip if already completed
        if _is_already_completed(db, CrewRun, uuid.UUID(run_id)):
            logger.info("CrewRun %s already in terminal state — skipping", run_id)
            return {"status": "skipped", "reason": "already_completed", "run_id": run_id}

        runner = CrewRunner(db)
        run = _run_async(runner.execute_run(uuid.UUID(run_id)))
        return {
            "run_id": str(run.id),
            "status": run.status,
            "findings_count": run.metrics.get("findings_count", 0) if run.metrics else 0,
            "duration_seconds": run.duration_seconds,
        }
    except Exception as exc:
        db.rollback()
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=30)
        raise
    finally:
        db.close()


@celery_app.task(
    name="mission.plan_and_start",
    queue="missions",
    bind=True,
    max_retries=2,
    soft_time_limit=3600,
    time_limit=3900,
)
def plan_and_start_mission(self, mission_id: str, run_id: str | None = None, correlation_id: str | None = None) -> dict:
    """Plan a mission, assemble crew, and execute."""
    if correlation_id:
        correlation_id_var.set(correlation_id)

    db = SessionLocal()
    try:
        mission = db.query(Mission).filter_by(id=uuid.UUID(mission_id)).first()
        if not mission:
            raise ValueError(f"Mission {mission_id} not found")

        # Idempotency: if run_id provided, check that specific run; else check latest
        if run_id:
            existing_run = db.query(MissionRun).filter_by(id=uuid.UUID(run_id)).first()
            if existing_run:
                status_val = existing_run.status.value if hasattr(existing_run.status, "value") else str(existing_run.status)
                if status_val in ("completed", "failed", "cancelled"):
                    logger.info("MissionRun %s already in terminal state — skipping", run_id)
                    return {"status": "skipped", "reason": "already_completed", "run_id": run_id}
                # Transition the existing run from created -> queued
                if status_val == "created":
                    existing_run.status = RunStatus.queued
                    db.commit()
        else:
            latest_run = (
                db.query(MissionRun)
                .filter_by(mission_id=uuid.UUID(mission_id))
                .order_by(MissionRun.created_at.desc())
                .first()
            )
            if latest_run:
                status_val = latest_run.status.value if hasattr(latest_run.status, "value") else str(latest_run.status)
                if status_val in ("completed", "failed", "cancelled"):
                    logger.info("MissionRun %s already in terminal state — skipping", latest_run.id)
                    return {"status": "skipped", "reason": "already_completed", "mission_id": mission_id}

        # Assemble crew
        crew = _run_async(assemble_crew(mission, db))

        # Start run
        run = _run_async(start_crew_run(crew, mission, db))

        # Execute
        runner = CrewRunner(db)
        completed_run = _run_async(runner.execute_run(run.id))

        return {
            "mission_id": str(mission.id),
            "crew_id": str(crew.id),
            "run_id": str(completed_run.id),
            "status": completed_run.status,
            "findings_count": completed_run.metrics.get("findings_count", 0) if completed_run.metrics else 0,
        }
    except Exception as exc:
        db.rollback()
        # Mark mission as failed
        mission = db.query(Mission).filter_by(id=uuid.UUID(mission_id)).first()
        if mission:
            mission.status = MissionStatus.failed
            db.commit()
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=30)
        raise
    finally:
        db.close()
