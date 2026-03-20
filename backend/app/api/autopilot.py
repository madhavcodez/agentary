from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models.user import User
from ..schemas.research import (
    AutopilotRunResult,
    AutopilotScheduleResponse,
    AutopilotScheduleUpdate,
    AutopilotStatus,
    AutopilotToggleResponse,
)

router = APIRouter(prefix="/autopilot", tags=["autopilot"])


def _get_user_or_404(db: Session, user_id: UUID) -> User:
    """Retrieve a user by ID or raise 404."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/run", response_model=AutopilotRunResult)
async def run_autopilot(
    user_id: UUID | None = Query(None, description="Scope cycle to a specific user"),
    db: Session = Depends(get_db),
):
    """Trigger one complete autopilot cycle.

    Sequentially: ingest -> score -> research -> create campaigns.
    Returns counts for each step.
    """
    from ..services.autopilot import run_autopilot_cycle

    result = await run_autopilot_cycle(db, user_id=user_id)
    return AutopilotRunResult(**result)


@router.get("/status", response_model=AutopilotStatus)
def autopilot_status(
    user_id: UUID | None = Query(None, description="Scope status to a specific user"),
):
    """Get the last autopilot run status and timing info."""
    from ..services.autopilot import get_autopilot_status

    status = get_autopilot_status(user_id=user_id)
    return AutopilotStatus(
        last_run=status.get("last_run"),
        last_result=(
            AutopilotRunResult(**status["last_result"])
            if status.get("last_result")
            else None
        ),
        running=status.get("running", False),
    )


# ---------------------------------------------------------------------------
# Schedule management endpoints
# ---------------------------------------------------------------------------


@router.get("/schedule", response_model=AutopilotScheduleResponse)
def get_schedule(
    user_id: UUID = Query(..., description="User ID"),
    db: Session = Depends(get_db),
):
    """Return the user's current autopilot schedule settings."""
    user = _get_user_or_404(db, user_id)
    return AutopilotScheduleResponse(
        autopilot_enabled=user.autopilot_enabled,
        autopilot_cron=user.autopilot_cron,
        autopilot_timezone=user.autopilot_timezone,
        autopilot_business_hours_only=user.autopilot_business_hours_only,
    )


@router.put("/schedule", response_model=AutopilotScheduleResponse)
def update_schedule(
    body: AutopilotScheduleUpdate,
    user_id: UUID = Query(..., description="User ID"),
    db: Session = Depends(get_db),
):
    """Update the user's autopilot cron, timezone, and business-hours preference.

    If autopilot is enabled, the scheduler job is replaced with the new settings.
    """
    from ..services.scheduler import add_autopilot_job, remove_autopilot_job

    user = _get_user_or_404(db, user_id)

    if body.autopilot_cron is not None:
        user.autopilot_cron = body.autopilot_cron
    if body.autopilot_timezone is not None:
        user.autopilot_timezone = body.autopilot_timezone
    if body.autopilot_business_hours_only is not None:
        user.autopilot_business_hours_only = body.autopilot_business_hours_only

    db.commit()
    db.refresh(user)

    # If autopilot is enabled, replace the scheduler job with updated settings
    if user.autopilot_enabled and user.autopilot_cron:
        remove_autopilot_job(str(user.id))
        add_autopilot_job(
            user_id=str(user.id),
            cron_expr=user.autopilot_cron,
            timezone=user.autopilot_timezone,
        )

    return AutopilotScheduleResponse(
        autopilot_enabled=user.autopilot_enabled,
        autopilot_cron=user.autopilot_cron,
        autopilot_timezone=user.autopilot_timezone,
        autopilot_business_hours_only=user.autopilot_business_hours_only,
    )


@router.post("/enable", response_model=AutopilotToggleResponse)
def enable_autopilot(
    user_id: UUID = Query(..., description="User ID"),
    db: Session = Depends(get_db),
):
    """Enable the user's autopilot schedule.

    Requires that ``autopilot_cron`` has been set via PUT /autopilot/schedule first.
    """
    from ..services.scheduler import add_autopilot_job

    user = _get_user_or_404(db, user_id)

    if not user.autopilot_cron:
        raise HTTPException(
            status_code=400,
            detail="Set a cron schedule via PUT /autopilot/schedule before enabling",
        )

    user.autopilot_enabled = True
    db.commit()

    add_autopilot_job(
        user_id=str(user.id),
        cron_expr=user.autopilot_cron,
        timezone=user.autopilot_timezone,
    )

    return AutopilotToggleResponse(
        autopilot_enabled=True,
        message="Autopilot enabled",
    )


@router.post("/disable", response_model=AutopilotToggleResponse)
def disable_autopilot(
    user_id: UUID = Query(..., description="User ID"),
    db: Session = Depends(get_db),
):
    """Disable the user's autopilot schedule and remove the scheduler job."""
    from ..services.scheduler import remove_autopilot_job

    user = _get_user_or_404(db, user_id)

    user.autopilot_enabled = False
    db.commit()

    remove_autopilot_job(str(user.id))

    return AutopilotToggleResponse(
        autopilot_enabled=False,
        message="Autopilot disabled",
    )
