"""API routes for action requests -- create, list, approve, reject, cancel."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.user import User
from ..schemas.actions import ActionReject, ActionRequestCreate
from ..services.actions.action_service import ActionService

router = APIRouter(prefix="/api/actions", tags=["actions"])


@router.post("")
def create_action(
    body: ActionRequestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    svc = ActionService(db)
    action = svc.create_action_request(
        project_id=body.project_id,
        user_id=user.id,
        action_type=body.action_type,
        title=body.title,
        description=body.description,
        parameters=body.parameters,
        recommendation_id=body.recommendation_id,
        entity_id=body.entity_id,
        confidence=body.confidence or 1.0,
        priority=body.priority or "medium",
    )
    db.commit()
    return _serialize(action)


@router.get("")
def list_actions(
    project_id: UUID | None = None,
    status: str | None = None,
    action_type: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[dict]:
    svc = ActionService(db)
    actions = svc.list_actions(
        project_id=project_id,
        status=status,
        action_type=action_type,
        limit=limit,
        offset=offset,
    )
    return [_serialize(a) for a in actions]


@router.get("/pending")
def get_pending(
    project_id: UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    svc = ActionService(db)
    actions = svc.get_pending(user.id, project_id=project_id)
    return [_serialize(a) for a in actions]


@router.get("/{action_id}")
def get_action(
    action_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    from ..models.action_request import ActionRequest

    action = db.query(ActionRequest).filter_by(id=action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    return _serialize(action)


@router.put("/{action_id}/approve")
def approve_action(
    action_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    svc = ActionService(db)
    try:
        action = svc.approve(action_id, user.id)
        db.commit()
        return _serialize(action)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put("/{action_id}/reject")
def reject_action(
    action_id: UUID,
    body: ActionReject,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    svc = ActionService(db)
    try:
        action = svc.reject(action_id, user.id, body.reason)
        db.commit()
        return _serialize(action)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put("/{action_id}/cancel")
def cancel_action(
    action_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    svc = ActionService(db)
    try:
        action = svc.cancel(action_id)
        db.commit()
        return _serialize(action)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


def _serialize(a) -> dict:
    return {
        "id": str(a.id),
        "project_id": str(a.project_id),
        "recommendation_id": str(a.recommendation_id) if a.recommendation_id else None,
        "entity_id": str(a.entity_id) if a.entity_id else None,
        "user_id": str(a.user_id),
        "action_type": (
            a.action_type.value if hasattr(a.action_type, "value") else str(a.action_type)
        ),
        "title": a.title,
        "description": a.description,
        "parameters": a.parameters,
        "confidence": a.confidence,
        "priority": a.priority,
        "requires_approval": a.requires_approval,
        "status": a.status.value if hasattr(a.status, "value") else str(a.status),
        "state_transitions": a.state_transitions,
        "policy_id": str(a.policy_id) if a.policy_id else None,
        "approved_by": str(a.approved_by) if a.approved_by else None,
        "approved_at": a.approved_at.isoformat() if a.approved_at else None,
        "expires_at": a.expires_at.isoformat() if a.expires_at else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }
