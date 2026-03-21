from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..deps import get_db, get_current_user
from ..models.user import User
from ..models.workflow import Workflow
from ..schemas.workflow import WorkflowCreate, WorkflowUpdate, WorkflowResponse

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


@router.post("", response_model=WorkflowResponse, status_code=201)
def create_workflow(
    body: WorkflowCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    wf = Workflow(user_id=user.id, **body.model_dump())
    db.add(wf)
    db.commit()
    db.refresh(wf)
    return wf


@router.get("", response_model=list[WorkflowResponse])
def list_workflows(
    category: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Workflow).filter(
        (Workflow.user_id == user.id) | (Workflow.is_template == True)
    )
    if category:
        query = query.filter(Workflow.category == category)
    return query.order_by(Workflow.created_at.desc()).all()


@router.get("/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(
    workflow_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@router.put("/{workflow_id}", response_model=WorkflowResponse)
def update_workflow(
    workflow_id: UUID,
    body: WorkflowUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    wf = db.query(Workflow).filter(Workflow.id == workflow_id, Workflow.user_id == user.id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(wf, key, value)
    wf.version += 1
    db.commit()
    db.refresh(wf)
    return wf
