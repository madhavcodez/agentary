from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..deps import get_db, get_current_user
from ..models.user import User
from ..models.finding import Finding
from ..schemas.finding import FindingCreate, FindingResponse

router = APIRouter(prefix="/api/findings", tags=["findings"])


@router.post("", response_model=FindingResponse, status_code=201)
def create_finding(
    body: FindingCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    finding = Finding(**body.model_dump())
    db.add(finding)
    db.commit()
    db.refresh(finding)
    return finding


@router.get("", response_model=list[FindingResponse])
def list_findings(
    project_id: UUID | None = None,
    mission_id: UUID | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    query = db.query(Finding)
    if project_id:
        query = query.filter(Finding.project_id == project_id)
    if mission_id:
        query = query.filter(Finding.mission_id == mission_id)
    return query.order_by(Finding.created_at.desc()).limit(100).all()
