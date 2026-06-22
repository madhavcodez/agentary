"""API routes for alerts."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.monitor import Alert, Monitor

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


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


@router.get("")
def list_alerts(
    severity: str | None = None,
    acknowledged: bool | None = None,
    project_id: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List alerts for the current user, filterable by severity/acknowledged/project."""
    # Join with Monitor to scope by user
    q = (
        db.query(Alert)
        .join(Monitor, Alert.monitor_id == Monitor.id)
        .filter(Monitor.user_id == user.id)
    )
    if severity:
        q = q.filter(Alert.severity == severity)
    if acknowledged is not None:
        q = q.filter(Alert.acknowledged == acknowledged)
    if project_id:
        q = q.filter(Alert.project_id == project_id)

    alerts = q.order_by(Alert.created_at.desc()).offset(offset).limit(limit).all()
    return [_alert_response(a) for a in alerts]


@router.put("/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: str,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark an alert as acknowledged."""
    alert = (
        db.query(Alert)
        .join(Monitor, Alert.monitor_id == Monitor.id)
        .filter(Alert.id == alert_id, Monitor.user_id == user.id)
        .first()
    )
    if not alert:
        raise HTTPException(404, "Alert not found")

    alert.acknowledged = True
    alert.acknowledged_at = datetime.now(UTC)
    alert.acknowledged_by = user.id
    db.commit()
    db.refresh(alert)
    return _alert_response(alert)


@router.get("/unread")
def unread_count(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return count of unacknowledged alerts."""
    count = (
        db.query(func.count(Alert.id))
        .join(Monitor, Alert.monitor_id == Monitor.id)
        .filter(Monitor.user_id == user.id, Alert.acknowledged == False)  # noqa: E712
        .scalar()
    )
    return {"unread": count}
