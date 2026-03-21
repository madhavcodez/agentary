"""Celery tasks for crew execution."""
from __future__ import annotations

import asyncio
import uuid

from ..celery_app import celery_app
from ..database import SessionLocal
from ..services.crews.crew_runner import CrewRunner
from ..services.crews.crew_service import assemble_crew, start_crew_run
from ..models.mission import Mission, MissionStatus


def _run_async(coro):
    """Run an async coroutine in a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    name="crew.execute_run",
    queue="crew_runs",
    bind=True,
    max_retries=2,
    soft_time_limit=3600,
    time_limit=3900,
)
def execute_crew_run(self, run_id: str) -> dict:
    """Execute a crew run in the background."""
    db = SessionLocal()
    try:
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
    queue="crew_runs",
)
def plan_and_start_mission(mission_id: str) -> dict:
    """Plan a mission, assemble crew, and execute."""
    db = SessionLocal()
    try:
        mission = db.query(Mission).filter_by(id=uuid.UUID(mission_id)).first()
        if not mission:
            raise ValueError(f"Mission {mission_id} not found")

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
    except Exception:
        db.rollback()
        # Mark mission as failed
        mission = db.query(Mission).filter_by(id=uuid.UUID(mission_id)).first()
        if mission:
            mission.status = MissionStatus.failed
            db.commit()
        raise
    finally:
        db.close()
