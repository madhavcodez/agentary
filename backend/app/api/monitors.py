from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.monitor import Alert, Monitor
from ..models.user import User
from ..schemas.monitor import AlertResponse, MonitorCreate, MonitorResponse

router = APIRouter(prefix="/api/monitors", tags=["monitors"])


@router.post("", response_model=MonitorResponse, status_code=201)
def create_monitor(
    body: MonitorCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    monitor = Monitor(user_id=user.id, **body.model_dump())
    db.add(monitor)
    db.commit()
    db.refresh(monitor)
    return monitor


@router.get("", response_model=list[MonitorResponse])
def list_monitors(
    project_id: UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Monitor).filter(Monitor.user_id == user.id)
    if project_id:
        query = query.filter(Monitor.project_id == project_id)
    return query.order_by(Monitor.created_at.desc()).all()


@router.get("/{monitor_id}/alerts", response_model=list[AlertResponse])
def list_alerts(
    monitor_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return db.query(Alert).filter(Alert.monitor_id == monitor_id).order_by(Alert.created_at.desc()).all()
