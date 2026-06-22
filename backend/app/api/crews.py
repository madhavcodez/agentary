"""API routes for agent crews and crew runs."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_session
from ..deps import get_current_user
from ..models.agent_crew import AgentActivity, AgentCrew
from ..models.crew_run import CrewRun
from ..models.crew_task import CrewTask
from ..models.expert_agent import ExpertAgent
from ..models.mission import Mission
from ..models.user import User

router = APIRouter(prefix="/api/crews", tags=["crews"])


@router.get("/{crew_id}/runs")
async def list_crew_runs(
    crew_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """List all runs for a crew."""
    crew = db.query(AgentCrew).filter_by(id=uuid.UUID(crew_id)).first()
    if not crew:
        raise HTTPException(404, "Crew not found")

    # Verify ownership through mission
    mission = db.query(Mission).filter_by(id=crew.mission_id, user_id=user.id).first()
    if not mission:
        raise HTTPException(404, "Crew not found")

    runs = (
        db.query(CrewRun)
        .filter_by(crew_id=crew.id)
        .order_by(CrewRun.created_at.desc())
        .all()
    )

    return {
        "crew_id": str(crew.id),
        "runs": [
            {
                "id": str(r.id),
                "status": r.status,
                "trigger_type": r.trigger_type,
                "iteration": r.iteration,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "duration_seconds": r.duration_seconds,
                "summary": r.summary,
                "metrics": r.metrics,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in runs
        ],
    }


@router.get("/{crew_id}/runs/{run_id}")
async def get_crew_run(
    crew_id: str,
    run_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Get detailed run info with task timeline and thinking_logs."""
    crew = db.query(AgentCrew).filter_by(id=uuid.UUID(crew_id)).first()
    if not crew:
        raise HTTPException(404, "Crew not found")

    mission = db.query(Mission).filter_by(id=crew.mission_id, user_id=user.id).first()
    if not mission:
        raise HTTPException(404, "Crew not found")

    run = db.query(CrewRun).filter_by(id=uuid.UUID(run_id), crew_id=crew.id).first()
    if not run:
        raise HTTPException(404, "Run not found")

    tasks = db.query(CrewTask).filter_by(run_id=run.id).all()
    task_details = []
    for task in tasks:
        expert = db.query(ExpertAgent).filter_by(id=task.expert_agent_id).first()
        task_details.append({
            "id": str(task.id),
            "expert_name": expert.name if expert else "Unknown",
            "expert_icon": expert.icon if expert else "\U0001f916",
            "expert_slug": expert.slug if expert else None,
            "task_type": task.task_type,
            "description": task.description,
            "status": task.status,
            "thinking_log": task.thinking_log or [],
            "output_data": task.output_data,
            "findings_produced": task.findings_produced,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "duration_seconds": task.duration_seconds,
            "tokens_used": task.tokens_used,
            "error_message": task.error_message,
        })

    return {
        "id": str(run.id),
        "crew_id": str(crew.id),
        "mission_id": str(mission.id),
        "status": run.status,
        "trigger_type": run.trigger_type,
        "iteration": run.iteration,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "duration_seconds": run.duration_seconds,
        "summary": run.summary,
        "metrics": run.metrics,
        "error": run.error,
        "tasks": task_details,
    }


@router.get("/{crew_id}/runs/{run_id}/live")
async def get_live_status(
    crew_id: str,
    run_id: str,
    after: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Poll for live status updates. Returns new activities since `after` timestamp."""
    crew = db.query(AgentCrew).filter_by(id=uuid.UUID(crew_id)).first()
    if not crew:
        raise HTTPException(404, "Crew not found")

    mission = db.query(Mission).filter_by(id=crew.mission_id, user_id=user.id).first()
    if not mission:
        raise HTTPException(404, "Crew not found")

    run = db.query(CrewRun).filter_by(id=uuid.UUID(run_id), crew_id=crew.id).first()
    if not run:
        raise HTTPException(404, "Run not found")

    # Get recent activities for this run
    query = (
        db.query(AgentActivity)
        .filter_by(run_id=run.id)
        .order_by(AgentActivity.created_at.asc())
    )

    if after:
        from datetime import datetime
        try:
            after_dt = datetime.fromisoformat(after)
            query = query.filter(AgentActivity.created_at > after_dt)
        except ValueError:
            pass

    activities = query.limit(100).all()

    # Get current task statuses
    tasks = db.query(CrewTask).filter_by(run_id=run.id).all()
    task_statuses = []
    for task in tasks:
        expert = db.query(ExpertAgent).filter_by(id=task.expert_agent_id).first()
        task_statuses.append({
            "task_id": str(task.id),
            "expert_name": expert.name if expert else "Unknown",
            "expert_icon": expert.icon if expert else "\U0001f916",
            "status": task.status,
            "findings_produced": task.findings_produced,
        })

    return {
        "run_status": run.status,
        "tasks": task_statuses,
        "activities": [
            {
                "id": str(a.id),
                "activity_type": a.activity_type.value if a.activity_type else "thinking",
                "content": a.content,
                "metadata": a.metadata_json,
                "confidence": a.confidence,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in activities
        ],
        "has_more": len(activities) == 100,
    }
