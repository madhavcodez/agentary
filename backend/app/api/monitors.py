"""API routes for monitor CRUD and operations."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.monitor import Alert, Monitor
from ..services.monitor_service import (
    create_monitor,
    execute_check,
    pause_monitor,
    resume_monitor,
    update_monitor,
)

router = APIRouter(prefix="/api/monitors", tags=["monitors"])


# ── Schemas ─────────────────────────────────────────────────────────

class MonitorCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = None
    monitor_type: str = Field(
        ...,
        pattern="^(web_content|api_data|price_tracker|listing_watcher|competitor_tracker|custom)$",
    )
    project_id: str | None = None
    check_config: dict = Field(default_factory=dict)
    alert_config: dict = Field(default_factory=dict)
    schedule_cron: str | None = None
    timezone: str = "UTC"


class MonitorUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    monitor_type: str | None = None
    check_config: dict | None = None
    alert_config: dict | None = None
    schedule_cron: str | None = None
    timezone: str | None = None


def _monitor_response(m: Monitor) -> dict:
    return {
        "id": str(m.id),
        "user_id": str(m.user_id),
        "project_id": str(m.project_id) if m.project_id else None,
        "name": m.name,
        "description": m.description,
        "monitor_type": m.monitor_type,
        "status": m.status,
        "check_config": m.check_config,
        "alert_config": m.alert_config,
        "schedule_cron": m.schedule_cron,
        "timezone": m.timezone,
        "last_check_at": m.last_check_at.isoformat() if m.last_check_at else None,
        "last_change_at": m.last_change_at.isoformat() if m.last_change_at else None,
        "total_checks": m.total_checks,
        "total_alerts": m.total_alerts,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "updated_at": m.updated_at.isoformat() if m.updated_at else None,
    }


def _alert_response(a: Alert) -> dict:
    return {
        "id": str(a.id),
        "monitor_id": str(a.monitor_id),
        "project_id": str(a.project_id) if a.project_id else None,
        "alert_type": a.alert_type,
        "title": a.title,
        "message": a.message,
        "severity": a.severity,
        "data": a.data,
        "acknowledged": a.acknowledged,
        "acknowledged_at": a.acknowledged_at.isoformat() if a.acknowledged_at else None,
        "delivered_channels": a.delivered_channels,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


# ── Routes ──────────────────────────────────────────────────────────

@router.post("")
def create(body: MonitorCreate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    m = create_monitor(db, user.id, body.model_dump())
    return _monitor_response(m)


@router.get("")
def list_monitors(
    status: str | None = None,
    project_id: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Monitor).filter(Monitor.user_id == user.id)
    if status:
        q = q.filter(Monitor.status == status)
    if project_id:
        q = q.filter(Monitor.project_id == project_id)
    monitors = q.order_by(Monitor.created_at.desc()).all()
    return [_monitor_response(m) for m in monitors]


@router.get("/{monitor_id}")
def get_monitor(monitor_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    m = db.query(Monitor).filter(Monitor.id == monitor_id, Monitor.user_id == user.id).first()
    if not m:
        raise HTTPException(404, "Monitor not found")
    return _monitor_response(m)


@router.put("/{monitor_id}")
def update(
    monitor_id: str,
    body: MonitorUpdate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    m = db.query(Monitor).filter(Monitor.id == monitor_id, Monitor.user_id == user.id).first()
    if not m:
        raise HTTPException(404, "Monitor not found")
    updated = update_monitor(db, m, body.model_dump(exclude_none=True))
    return _monitor_response(updated)


@router.delete("/{monitor_id}")
def delete(monitor_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    m = db.query(Monitor).filter(Monitor.id == monitor_id, Monitor.user_id == user.id).first()
    if not m:
        raise HTTPException(404, "Monitor not found")

    from ..services.scheduler import remove_monitor_job
    remove_monitor_job(str(m.id))

    db.delete(m)
    db.commit()
    return {"status": "deleted"}


@router.post("/{monitor_id}/check")
async def trigger_check(monitor_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    m = db.query(Monitor).filter(Monitor.id == monitor_id, Monitor.user_id == user.id).first()
    if not m:
        raise HTTPException(404, "Monitor not found")
    result = await execute_check(str(m.id), db)
    return result


@router.post("/{monitor_id}/pause")
def do_pause(monitor_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    m = db.query(Monitor).filter(Monitor.id == monitor_id, Monitor.user_id == user.id).first()
    if not m:
        raise HTTPException(404, "Monitor not found")
    return _monitor_response(pause_monitor(db, m))


@router.post("/{monitor_id}/resume")
def do_resume(monitor_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    m = db.query(Monitor).filter(Monitor.id == monitor_id, Monitor.user_id == user.id).first()
    if not m:
        raise HTTPException(404, "Monitor not found")
    return _monitor_response(resume_monitor(db, m))


@router.get("/{monitor_id}/alerts")
def get_monitor_alerts(
    monitor_id: str,
    limit: int = Query(50, ge=1, le=200),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    m = db.query(Monitor).filter(Monitor.id == monitor_id, Monitor.user_id == user.id).first()
    if not m:
        raise HTTPException(404, "Monitor not found")
    alerts = (
        db.query(Alert)
        .filter(Alert.monitor_id == m.id)
        .order_by(Alert.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_alert_response(a) for a in alerts]


@router.get("/{monitor_id}/history")
def get_monitor_history(
    monitor_id: str,
    limit: int = Query(50, ge=1, le=200),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    m = db.query(Monitor).filter(Monitor.id == monitor_id, Monitor.user_id == user.id).first()
    if not m:
        raise HTTPException(404, "Monitor not found")
    return {
        "monitor_id": str(m.id),
        "total_checks": m.total_checks,
        "total_alerts": m.total_alerts,
        "last_check_at": m.last_check_at.isoformat() if m.last_check_at else None,
        "last_change_at": m.last_change_at.isoformat() if m.last_change_at else None,
        "last_snapshot": m.last_snapshot,
    }
