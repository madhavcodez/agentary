from __future__ import annotations

import logging
import uuid

from ..database import SessionLocal
from ..models.mission_run import MissionRun
from .celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.mission_runs.execute_mission",
    bind=True,
    max_retries=2,
    soft_time_limit=3600,
    time_limit=3900,
)
def execute_mission(self, mission_id: str, run_id: str) -> dict:
    """Execute a mission run with idempotency guard."""
    db = SessionLocal()
    try:
        # Idempotency check — skip if already in a terminal state
        run = db.query(MissionRun).filter_by(id=uuid.UUID(run_id)).first()
        if run:
            status_val = run.status.value if hasattr(run.status, "value") else str(run.status)
            if status_val in ("completed", "failed", "cancelled"):
                logger.info("MissionRun %s already in terminal state (%s) — skipping", run_id, status_val)
                return {"status": "skipped", "reason": "already_completed", "run_id": run_id}

        # Delegate to plan_and_start_mission for actual execution
        from .crew_tasks import plan_and_start_mission
        return plan_and_start_mission(mission_id)
    except Exception as exc:
        db.rollback()
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=30) from exc
        raise
    finally:
        db.close()
