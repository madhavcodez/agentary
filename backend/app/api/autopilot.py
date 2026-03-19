from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import get_db
from ..schemas.research import AutopilotRunResult, AutopilotStatus

router = APIRouter(prefix="/autopilot", tags=["autopilot"])


@router.post("/run", response_model=AutopilotRunResult)
async def run_autopilot(db: Session = Depends(get_db)):
    """Trigger one complete autopilot cycle.

    Sequentially: ingest -> score -> research -> create campaigns.
    Returns counts for each step.
    """
    from ..services.autopilot import run_autopilot_cycle

    result = await run_autopilot_cycle(db)
    return AutopilotRunResult(**result)


@router.get("/status", response_model=AutopilotStatus)
def autopilot_status():
    """Get the last autopilot run status and timing info."""
    from ..services.autopilot import get_autopilot_status

    status = get_autopilot_status()
    return AutopilotStatus(
        last_run=status.get("last_run"),
        last_result=(
            AutopilotRunResult(**status["last_result"])
            if status.get("last_result")
            else None
        ),
        running=status.get("running", False),
    )
