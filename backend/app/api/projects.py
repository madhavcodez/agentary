from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..core.background_tasks import spawn_background_task as _spawn_background_task
from ..core.correlation import get_correlation_id
from ..core.rate_limiter import limiter
from ..deps import get_current_user, get_db
from ..models.project import Project, ProjectStatus
from ..models.user import User
from ..schemas.onboarding import (
    ConfigureAndStartRequest,
    ConfigureAndStartResponse,
    GenerateQuestionsRequest,
    GenerateQuestionsResponse,
)
from ..schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _mission_response(project: Project, mission) -> dict:
    """Build a standardized configure-and-start response dict."""
    return {
        "project": {
            "id": str(project.id),
            "name": project.name,
            "domain_context": project.domain_context,
            "status": (
                project.status.value if hasattr(project.status, "value") else str(project.status)
            ),
            "total_missions": project.total_missions,
        },
        "mission": {
            "id": str(mission.id),
            "name": mission.name,
            "status": (
                mission.status.value if hasattr(mission.status, "value") else str(mission.status)
            ),
            "objective": mission.objective,
            "created_at": mission.created_at.isoformat() if mission.created_at else None,
        },
    }


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(
    body: ProjectCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = Project(user_id=user.id, **body.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    status: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Project).filter(Project.user_id == user.id)
    if status:
        query = query.filter(Project.status == status)
    return query.order_by(Project.created_at.desc()).all()


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: UUID,
    body: ProjectUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}")
def delete_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.status = ProjectStatus.archived
    db.commit()
    return {"status": "archived"}


# ── Onboarding Endpoints ────────────────────────────────────────────


@router.post("/{project_id}/generate-questions", response_model=GenerateQuestionsResponse)
@limiter.limit("10/minute")
async def generate_questions(
    request: Request,
    project_id: UUID,
    body: GenerateQuestionsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Call Gemini to generate smart onboarding questions for a project."""
    from ..services.onboarding import generate_onboarding_questions

    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return await generate_onboarding_questions(project, body.title, body.project_type)


@router.post("/{project_id}/configure-and-start", response_model=ConfigureAndStartResponse)
async def configure_and_start(
    project_id: UUID,
    body: ConfigureAndStartRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Take answered onboarding questions, configure the project, create a mission, and start it."""
    from ..models.mission import Mission
    from ..services.crews.crew_service import assemble_crew, start_crew_run
    from ..services.onboarding import create_mission_for_project, synthesize_domain_context

    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # ── Deduplication: reject if a mission was created in the last 30s ──
    dedup_cutoff = datetime.now(UTC) - timedelta(seconds=30)
    recent_mission = (
        db.query(Mission)
        .filter(
            Mission.project_id == project.id,
            Mission.user_id == user.id,
            Mission.created_at >= dedup_cutoff,
        )
        .order_by(Mission.created_at.desc())
        .first()
    )
    if recent_mission is not None:
        logger.info(
            "Dedup: returning existing mission %s for project %s", recent_mission.id, project_id
        )
        return _mission_response(project, recent_mission)

    # Synthesize domain context + create mission via service layer
    domain_context = await synthesize_domain_context(body.project_title, body.answers)
    mission = create_mission_for_project(project, user.id, domain_context, body.project_title, db)

    # Start the mission (assemble crew + trigger run)
    try:
        crew = await assemble_crew(mission, db)
        run = await start_crew_run(crew, mission, db)

        # Commit before dispatching so inline fallback can read committed data
        db.commit()

        # Enqueue Celery task with fallback
        try:
            from ..tasks.crew_tasks import execute_crew_run

            execute_crew_run.delay(str(run.id), correlation_id=get_correlation_id())
        except Exception as celery_exc:
            logger.warning("Celery unavailable, falling back to inline execution: %s", celery_exc)
            from ..models.mission_run import MissionRun
            from ..services.crews.crew_runner import CrewRunner

            async def _run_inline():
                from ..database import SessionLocal

                inline_db = SessionLocal()
                try:
                    runner = CrewRunner(inline_db)
                    await runner.execute_run(run.id)
                except Exception as exc:
                    logger.error(
                        "Inline crew run failed for run %s: %s", run.id, exc, exc_info=True
                    )
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

            _spawn_background_task(_run_inline(), "project-inline-run")
    except Exception as exc:
        db.rollback()
        logger.error("Failed to start mission %s: %s", mission.id, exc)
        raise HTTPException(
            status_code=500, detail="Failed to start mission. Please try again."
        ) from exc

    db.refresh(project)
    db.refresh(mission)

    return _mission_response(project, mission)
