from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.user import User
from ..schemas.research import AutopilotRunResult, AutopilotStatus

router = APIRouter(prefix="/autopilot", tags=["autopilot"])


@router.post("/run", response_model=AutopilotRunResult)
async def run_autopilot(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Trigger one complete autopilot cycle.

    Sequentially: ingest -> score -> research -> create campaigns.
    Returns counts for each step.
    """
    from ..services.autopilot import run_autopilot_cycle

    result = await run_autopilot_cycle(db, user_id=user.id)
    return AutopilotRunResult(**result)


@router.get("/status", response_model=AutopilotStatus)
def autopilot_status(user: User = Depends(get_current_user)):
    """Get the last autopilot run status and timing info."""
    from ..services.autopilot import get_autopilot_status

    status = get_autopilot_status(user_id=user.id)
    return AutopilotStatus(
        last_run=status.get("last_run"),
        last_result=(
            AutopilotRunResult(**status["last_result"])
            if status.get("last_result")
            else None
        ),
        running=status.get("running", False),
    )
