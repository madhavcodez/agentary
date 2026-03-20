from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.policy import Policy
from ..models.user import User
from ..schemas.policy import PolicyCreate, PolicyResponse, PolicyUpdate

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("", response_model=list[PolicyResponse])
def list_policies(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return (
        db.query(Policy)
        .filter(Policy.user_id == user.id)
        .order_by(Policy.created_at.desc())
        .all()
    )


@router.post("", response_model=PolicyResponse)
def create_policy(
    body: PolicyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    policy = Policy(
        user_id=user.id,
        name=body.name,
        rules_json=body.rules_json,
        description=body.description,
        is_active=body.is_active,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.get("/{policy_id}", response_model=PolicyResponse)
def get_policy(
    policy_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    policy = (
        db.query(Policy)
        .filter(Policy.id == policy_id, Policy.user_id == user.id)
        .first()
    )
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


@router.put("/{policy_id}", response_model=PolicyResponse)
def update_policy(
    policy_id: UUID,
    body: PolicyUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    policy = (
        db.query(Policy)
        .filter(Policy.id == policy_id, Policy.user_id == user.id)
        .first()
    )
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    if body.name is not None:
        policy.name = body.name
    if body.rules_json is not None:
        policy.rules_json = body.rules_json
    if body.description is not None:
        policy.description = body.description
    if body.is_active is not None:
        policy.is_active = body.is_active

    db.commit()
    db.refresh(policy)
    return policy


@router.delete("/{policy_id}")
def delete_policy(
    policy_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    policy = (
        db.query(Policy)
        .filter(Policy.id == policy_id, Policy.user_id == user.id)
        .first()
    )
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    db.delete(policy)
    db.commit()
    return {"status": "deleted"}
