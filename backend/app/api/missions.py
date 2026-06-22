from __future__ import annotations

import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..core.background_tasks import spawn_background_task as _spawn_background_task
from ..core.correlation import get_correlation_id
from ..deps import get_current_user, get_db
from ..models.agent_crew import AgentActivity, AgentCrew
from ..models.crew_run import CrewRun
from ..models.enums import RunStatus
from ..models.finding import Finding
from ..models.mission import Mission
from ..models.mission_run import MissionRun
from ..models.user import User
from ..schemas.mission import MissionCreate, MissionResponse, MissionUpdate
from ..schemas.mission_run import MissionRunResponse
from ..schemas.onboarding import SynthesizeReportResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/missions", tags=["missions"])


@router.post("", response_model=MissionResponse, status_code=201)
def create_mission(
    body: MissionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    mission = Mission(user_id=user.id, **body.model_dump())
    db.add(mission)
    db.commit()
    db.refresh(mission)
    return mission


@router.get("", response_model=list[MissionResponse])
def list_missions(
    project_id: UUID | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Mission).filter(Mission.user_id == user.id)
    if project_id:
        query = query.filter(Mission.project_id == project_id)
    if status:
        query = query.filter(Mission.status == status)
    return query.order_by(Mission.created_at.desc()).all()


@router.get("/{mission_id}", response_model=MissionResponse)
def get_mission(
    mission_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    mission = db.query(Mission).filter(Mission.id == mission_id, Mission.user_id == user.id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission


@router.put("/{mission_id}", response_model=MissionResponse)
def update_mission(
    mission_id: UUID,
    body: MissionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    mission = db.query(Mission).filter(Mission.id == mission_id, Mission.user_id == user.id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(mission, key, value)
    db.commit()
    db.refresh(mission)
    return mission


@router.post("/{mission_id}/run", status_code=202)
def trigger_mission_run(
    mission_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    mission = db.query(Mission).filter(Mission.id == mission_id, Mission.user_id == user.id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    correlation = uuid4()

    run = MissionRun(
        mission_id=mission.id,
        status=RunStatus.created,
        correlation_id=correlation,
    )
    db.add(run)
    db.flush()  # populate run.id before using it

    idempotency_key = f"mission_run:{mission_id}:{run.id}"
    run.idempotency_key = idempotency_key
    db.commit()
    db.refresh(run)

    # Dispatch Celery task with run_id for idempotent execution
    try:
        from ..tasks.crew_tasks import plan_and_start_mission
        plan_and_start_mission.delay(str(mission.id), str(run.id), correlation_id=get_correlation_id())
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(
            "Celery dispatch failed for mission %s, run %s: %s — task will need manual retry",
            mission_id, run.id, exc,
        )

    return JSONResponse(
        status_code=202,
        content={"run_id": str(run.id), "status": "queued"},
    )


@router.get("/{mission_id}/runs", response_model=list[MissionRunResponse])
def list_mission_runs(
    mission_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List runs for a mission. Verifies caller owns the mission first.

    Previously this filtered only on ``mission_id``, letting any authenticated
    user enumerate runs across the whole platform by guessing UUIDs. See
    SECURITY review IDOR #7.
    """
    mission = (
        db.query(Mission)
        .filter(Mission.id == mission_id, Mission.user_id == user.id)
        .first()
    )
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    return (
        db.query(MissionRun)
        .filter(MissionRun.mission_id == mission_id)
        .order_by(MissionRun.created_at.desc())
        .all()
    )


# ── Research Engine Endpoints ─────────────────────────────────────────


@router.post("/{mission_id}/start")
async def start_mission(
    mission_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Assemble expert crew and start research execution."""
    from ..models.mission import MissionStatus
    from ..services.crews.crew_service import assemble_crew, start_crew_run

    mission = db.query(Mission).filter(Mission.id == mission_id, Mission.user_id == user.id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    if mission.status.value not in ("draft", "failed", "paused"):
        raise HTTPException(status_code=400, detail=f"Cannot start mission in {mission.status.value} status")

    try:
        # Assemble crew
        crew_config = mission.crew_config or {}
        expert_slugs = crew_config.get("required_experts")
        crew = await assemble_crew(mission, db, expert_slugs=expert_slugs)

        # Start run
        run = await start_crew_run(crew, mission, db)

        # Enqueue Celery task (with fallback to inline execution)
        try:
            from ..tasks.crew_tasks import execute_crew_run
            execute_crew_run.delay(str(run.id), correlation_id=get_correlation_id())
        except Exception as celery_exc:
            logger.warning("Celery unavailable, falling back to inline execution: %s", celery_exc)
            from ..services.crews.crew_runner import CrewRunner

            async def _run_inline():
                from ..database import SessionLocal
                inline_db = SessionLocal()
                try:
                    runner = CrewRunner(inline_db)
                    await runner.execute_run(run.id)
                except Exception as exc:
                    logger.error("Inline crew run failed for run %s: %s", run.id, exc, exc_info=True)
                    try:
                        run_obj = inline_db.query(MissionRun).filter_by(id=run.id).first()
                        if run_obj and run_obj.status not in ("completed", "failed", "cancelled"):
                            run_obj.status = "failed"
                            run_obj.failure_message = str(exc)
                            inline_db.commit()
                    except Exception as db_exc:
                        logger.error("Failed to mark run %s as failed: %s", run.id, db_exc)
                        inline_db.rollback()
                finally:
                    inline_db.close()

            # create_task supersedes ensure_future in 3.10+; the named task
            # is held in a module-level set so the GC can't reclaim it mid-
            # flight (a known ensure_future foot-gun).
            _spawn_background_task(_run_inline(), "mission-inline-run")
    except Exception as exc:
        db.rollback()
        mission.status = MissionStatus.failed
        db.commit()
        raise HTTPException(status_code=500, detail="Failed to start mission. Please try again.") from exc

    return {
        "mission_id": str(mission.id),
        "crew_id": str(crew.id),
        "run_id": str(run.id),
        "status": "queued",
        "message": "Mission started — crew assembled and execution queued",
    }


@router.post("/{mission_id}/stop")
def stop_mission(
    mission_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Cancel a running mission."""
    from ..models.mission import MissionStatus

    mission = db.query(Mission).filter(Mission.id == mission_id, Mission.user_id == user.id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    mission.status = MissionStatus.paused
    runs = db.query(CrewRun).filter_by(mission_id=mission.id, status="running").all()
    for run in runs:
        run.status = "cancelled"
    db.commit()
    return {"status": "cancelled", "message": "Mission stopped"}


@router.get("/{mission_id}/findings")
def get_mission_findings(
    mission_id: UUID,
    category: str | None = None,
    confidence_min: float | None = None,
    source_type: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get findings for a mission with optional filters."""
    mission = db.query(Mission).filter(Mission.id == mission_id, Mission.user_id == user.id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    query = db.query(Finding).filter(Finding.mission_id == mission.id)
    if category:
        # Backward-compatible filter name; underlying model uses finding_type enum.
        query = query.filter(Finding.finding_type == category)
    if confidence_min is not None:
        query = query.filter(Finding.confidence >= confidence_min)
    if source_type:
        query = query.filter(Finding.source_type == source_type)

    findings = query.order_by(Finding.confidence.desc()).all()

    return {
        "mission_id": str(mission.id),
        "total": len(findings),
        "items": [
            {
                "id": str(f.id),
                # Keep "category" key for frontend compatibility.
                "category": f.finding_type.value if hasattr(f.finding_type, "value") else str(f.finding_type),
                "title": f.title,
                "content": f.content,
                "structured_data": f.structured_data,
                "source_type": f.source_type.value if hasattr(f.source_type, "value") else f.source_type,
                "source_url": f.source_url,
                "source_name": f.source_name,
                "confidence": f.confidence,
                "verified": f.verified,
                "tags": f.tags or [],
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in findings
        ],
    }


@router.get("/{mission_id}/findings/structured")
def get_structured_findings(
    mission_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get findings in a structured table format."""
    mission = db.query(Mission).filter(Mission.id == mission_id, Mission.user_id == user.id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    findings = db.query(Finding).filter(Finding.mission_id == mission.id).all()

    return {
        "mission_id": str(mission.id),
        "columns": ["title", "category", "confidence", "source", "content"],
        "rows": [
            {
                "id": str(f.id),
                "title": f.title,
                "category": f.finding_type.value if hasattr(f.finding_type, "value") else str(f.finding_type),
                "confidence": f.confidence,
                "source": f.source_name or f.source_url or "N/A",
                "content": f.content[:200] if f.content else "",
                "structured_data": f.structured_data,
            }
            for f in findings
        ],
    }


@router.get("/{mission_id}/status")
def get_mission_status(
    mission_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get real-time mission status with activity feed."""
    mission = db.query(Mission).filter(Mission.id == mission_id, Mission.user_id == user.id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    activities = (
        db.query(AgentActivity)
        .filter(AgentActivity.mission_id == mission.id)
        .order_by(AgentActivity.created_at.desc())
        .limit(50)
        .all()
    )

    crew = db.query(AgentCrew).filter_by(mission_id=mission.id).first()

    # Find the latest run for this mission (for step trace link)
    latest_run = (
        db.query(CrewRun)
        .filter(CrewRun.mission_id == mission.id)
        .order_by(CrewRun.created_at.desc())
        .first()
    )

    return {
        "mission_id": str(mission.id),
        "latest_run_id": str(latest_run.id) if latest_run else None,
        "status": mission.status.value if hasattr(mission.status, "value") else str(mission.status),
        "findings_count": mission.findings_count or 0,
        "confidence_score": mission.confidence_score,
        "crew": {"agents": crew.agents or []} if crew else None,
        "activities": [
            {
                "id": str(a.id),
                "activity_type": a.activity_type.value if hasattr(a.activity_type, "value") else str(a.activity_type),
                "content": a.content,
                "metadata": a.metadata_json,
                "confidence": a.confidence,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in activities
        ],
    }


@router.post("/{mission_id}/rerun")
async def rerun_mission(
    mission_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Re-run a completed or failed mission."""
    from ..models.mission import MissionStatus
    from ..services.crews.crew_service import assemble_crew, start_crew_run

    mission = db.query(Mission).filter(Mission.id == mission_id, Mission.user_id == user.id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    try:
        crew = db.query(AgentCrew).filter_by(mission_id=mission.id).first()
        if not crew:
            crew = await assemble_crew(mission, db)

        run = await start_crew_run(crew, mission, db)

        try:
            from ..tasks.crew_tasks import execute_crew_run
            execute_crew_run.delay(str(run.id), correlation_id=get_correlation_id())
        except Exception as celery_exc:
            logger.warning("Celery unavailable for rerun, falling back to inline: %s", celery_exc)
            from ..services.crews.crew_runner import CrewRunner

            async def _run_inline():
                from ..database import SessionLocal
                inline_db = SessionLocal()
                try:
                    runner = CrewRunner(inline_db)
                    await runner.execute_run(run.id)
                except Exception as exc:
                    logger.error("Inline crew rerun failed for run %s: %s", run.id, exc, exc_info=True)
                    try:
                        run_obj = inline_db.query(MissionRun).filter_by(id=run.id).first()
                        if run_obj and run_obj.status not in ("completed", "failed", "cancelled"):
                            run_obj.status = "failed"
                            run_obj.failure_message = str(exc)
                            inline_db.commit()
                    except Exception as db_exc:
                        logger.error("Failed to mark rerun %s as failed: %s", run.id, db_exc)
                        inline_db.rollback()
                finally:
                    inline_db.close()

            # create_task supersedes ensure_future in 3.10+; the named task
            # is held in a module-level set so the GC can't reclaim it mid-
            # flight (a known ensure_future foot-gun).
            _spawn_background_task(_run_inline(), "mission-inline-run")
    except Exception as exc:
        db.rollback()
        mission.status = MissionStatus.failed
        db.commit()
        raise HTTPException(status_code=500, detail="Failed to rerun mission. Please try again.") from exc

    return {
        "mission_id": str(mission.id),
        "run_id": str(run.id),
        "status": "queued",
        "message": "Mission re-run queued",
    }


# ── Report Synthesis Endpoint ────────────────────────────────────────


@router.post("/{mission_id}/synthesize-report", response_model=SynthesizeReportResponse)
async def synthesize_report(
    mission_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Synthesize a report from all mission findings using Gemini.

    If STORM is enabled for this mission and a :class:`ResearchOutline`
    exists, routes through :func:`synthesize_report_from_outline` which
    produces a cited, section-level report. Otherwise falls back to the
    legacy single-pass path.
    """
    from ..services.report_synthesis import (
        synthesize_report_from_findings,
        synthesize_report_from_outline,
    )
    from ..services.storm import should_run_storm

    mission = db.query(Mission).filter(Mission.id == mission_id, Mission.user_id == user.id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    try:
        report = None
        if should_run_storm(mission):
            from ..models.research_outline import ResearchOutline

            outline = (
                db.query(ResearchOutline)
                .filter(ResearchOutline.mission_id == mission.id)
                .order_by(ResearchOutline.version.desc())
                .first()
            )
            if outline is not None:
                try:
                    report = await synthesize_report_from_outline(
                        mission, outline, user.id, db
                    )
                except Exception as exc:
                    logger.warning(
                        "STORM synthesis failed for mission %s, falling back to legacy: %s",
                        mission_id,
                        exc,
                    )
                    report = None
        if report is None:
            report = await synthesize_report_from_findings(mission, user.id, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail="AI report synthesis failed. Please try again.") from exc
    except Exception as exc:
        db.rollback()
        logger.error("Failed to save synthesized report for mission %s: %s", mission_id, exc)
        raise HTTPException(status_code=500, detail="Failed to save report. Please try again.") from exc

    return {
        "report": {
            "id": str(report.id),
            "title": report.title,
            "status": report.status,
            "executive_summary": report.executive_summary,
            "sections": report.sections,
            "content_markdown": report.content_markdown,
            "sources": report.sources,
            "methodology": report.methodology,
            "created_at": report.created_at.isoformat() if report.created_at else None,
        },
    }
