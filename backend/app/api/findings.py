from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.finding import Finding
from ..models.project import Project
from ..models.user import User
from ..schemas.finding import FindingCreate, FindingResponse

router = APIRouter(prefix="/api/findings", tags=["findings"])


@router.post("", response_model=FindingResponse, status_code=201)
def create_finding(
    body: FindingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a finding. Verifies the caller owns the parent project before write."""
    project_id = getattr(body, "project_id", None)
    if project_id is None:
        raise HTTPException(status_code=400, detail="project_id is required")

    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    finding = Finding(**body.model_dump())
    db.add(finding)
    db.commit()
    db.refresh(finding)
    return finding


@router.get("", response_model=list[FindingResponse])
def list_findings(
    project_id: UUID | None = None,
    mission_id: UUID | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List findings scoped to the caller's projects.

    Without the join to Project on ``user_id`` any authenticated user could
    enumerate findings across the whole platform by omitting both filters or
    guessing a mission UUID. See SECURITY review item #6.
    """
    query = (
        db.query(Finding)
        .join(Project, Project.id == Finding.project_id)
        .filter(Project.user_id == user.id)
    )
    if project_id:
        query = query.filter(Finding.project_id == project_id)
    if mission_id:
        query = query.filter(Finding.mission_id == mission_id)
    return query.order_by(Finding.created_at.desc()).offset(offset).limit(limit).all()
