"""API endpoint for querying RunStep trace records."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.run_step import RunStep

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.get("/{run_id}/steps")
def get_run_steps(
    run_id: str,
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> list[dict]:
    """Return RunSteps for a run, ordered by start time.

    A DeerFlow run with 6 iterations × 6 experts generates ~36 tool-call
    steps + phase steps; bounded at 1000 per page so a long-running mission
    doesn't return a multi-MB JSON blob.
    """
    steps = (
        db.query(RunStep)
        .filter(RunStep.run_id == run_id)
        .order_by(RunStep.started_at.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(s.id),
            "step_type": s.step_type.value if s.step_type else s.step_type,
            "step_name": s.step_name,
            "status": s.status,
            "input_summary": s.input_summary,
            "output_summary": s.output_summary,
            "error": s.error,
            "tokens_used": s.tokens_used,
            "cost_usd": s.cost_usd,
            "duration_ms": s.duration_ms,
            "parent_step_id": str(s.parent_step_id) if s.parent_step_id else None,
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
        }
        for s in steps
    ]
