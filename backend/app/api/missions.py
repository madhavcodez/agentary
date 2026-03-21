from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..deps import get_db, get_current_user
from ..models.user import User
from ..models.mission import Mission
from ..models.mission_run import MissionRun
from ..schemas.mission import MissionCreate, MissionUpdate, MissionResponse
from ..schemas.mission_run import MissionRunResponse

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


@router.post("/{mission_id}/run", response_model=MissionRunResponse, status_code=201)
def trigger_mission_run(
    mission_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    mission = db.query(Mission).filter(Mission.id == mission_id, Mission.user_id == user.id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    run = MissionRun(mission_id=mission.id)
    db.add(run)
    db.commit()
    db.refresh(run)
    # TODO: Dispatch Celery task to execute the mission
    return run


@router.get("/{mission_id}/runs", response_model=list[MissionRunResponse])
def list_mission_runs(
    mission_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return db.query(MissionRun).filter(MissionRun.mission_id == mission_id).order_by(MissionRun.created_at.desc()).all()
