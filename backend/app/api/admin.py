"""Admin API routes for maintenance and migration tasks."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.user import User

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/migrate-findings")
def trigger_findings_migration(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger async migration of findings to observations. Idempotent."""
    try:
        from ..tasks.migration_tasks import migrate_findings_to_observations
        migrate_findings_to_observations.delay()
        return {"status": "migration_started"}
    except Exception:
        return {
            "status": "celery_unavailable",
            "message": "Run manually with migrate_findings_to_observations()",
        }
