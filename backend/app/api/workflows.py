from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.user import User
from ..models.workflow import Workflow
from ..models.workflow_run import WorkflowRun
from ..schemas.workflow import (
    WorkflowCreate,
    WorkflowFromDescription,
    WorkflowFromTemplate,
    WorkflowList,
    WorkflowResponse,
    WorkflowRunList,
    WorkflowRunResponse,
    WorkflowUpdate,
)
from ..services.workflow import service as wf_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


# ── CRUD ─────────────────────────────────────────────────────────────

@router.post("", response_model=WorkflowResponse, status_code=201)
def create_workflow(
    body: WorkflowCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    workflow = wf_service.create_workflow(db, user.id, body.model_dump())
    return workflow


@router.get("", response_model=WorkflowList)
def list_workflows(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = None,
    project_id: UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Workflow).filter(Workflow.user_id == user.id)
    if status:
        query = query.filter(Workflow.status == status)
    if project_id:
        query = query.filter(Workflow.project_id == project_id)

    total = query.count()
    items = (
        query.order_by(Workflow.updated_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return WorkflowList(items=items, total=total, page=page, limit=limit)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(
    workflow_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.user_id == user.id)
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.put("/{workflow_id}", response_model=WorkflowResponse)
def update_workflow(
    workflow_id: UUID,
    body: WorkflowUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.user_id == user.id)
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    data = body.model_dump(exclude_none=True)
    workflow = wf_service.update_workflow(db, workflow, data)
    return workflow


@router.delete("/{workflow_id}")
def delete_workflow(
    workflow_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.user_id == user.id)
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    wf_service.delete_workflow(db, workflow)
    return {"status": "deleted"}


# ── Activation / Pause ───────────────────────────────────────────────

@router.post("/{workflow_id}/activate", response_model=WorkflowResponse)
def activate_workflow(
    workflow_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.user_id == user.id)
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    try:
        workflow = wf_service.activate_workflow(db, workflow)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return workflow


@router.post("/{workflow_id}/pause", response_model=WorkflowResponse)
def pause_workflow(
    workflow_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.user_id == user.id)
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    workflow = wf_service.pause_workflow(db, workflow)
    return workflow


# ── Run Management ───────────────────────────────────────────────────

@router.post("/{workflow_id}/run", response_model=WorkflowRunResponse)
async def trigger_run(
    workflow_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.user_id == user.id)
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    run = await wf_service.trigger_run(db, workflow)
    return run


@router.get("/{workflow_id}/runs", response_model=WorkflowRunList)
def list_runs(
    workflow_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.user_id == user.id)
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    query = db.query(WorkflowRun).filter(WorkflowRun.workflow_id == workflow_id)
    total = query.count()
    items = (
        query.order_by(WorkflowRun.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return WorkflowRunList(items=items, total=total, page=page, limit=limit)


@router.get("/{workflow_id}/runs/{run_id}", response_model=WorkflowRunResponse)
def get_run(
    workflow_id: UUID,
    run_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    run = (
        db.query(WorkflowRun)
        .filter(
            WorkflowRun.id == run_id,
            WorkflowRun.workflow_id == workflow_id,
            WorkflowRun.user_id == user.id,
        )
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return run


# ── From Template ────────────────────────────────────────────────────

@router.post("/from-template", response_model=WorkflowResponse, status_code=201)
def create_from_template(
    body: WorkflowFromTemplate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        workflow = wf_service.create_from_template(
            db, user.id, body.template_id, body.variables,
            project_id=body.project_id, name=body.name,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return workflow


# ── From Natural Language ────────────────────────────────────────────

@router.post("/from-description", response_model=WorkflowResponse, status_code=201)
async def create_from_description(
    body: WorkflowFromDescription,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        workflow = await wf_service.create_from_natural_language(
            db, user.id, body.description, project_id=body.project_id,
        )
    except Exception as exc:
        logger.exception("NL workflow generation failed")
        raise HTTPException(
            status_code=500,
            detail="Workflow generation failed; see server logs (correlation id)",
        ) from exc
    return workflow


# ── Validation ───────────────────────────────────────────────────────

@router.post("/{workflow_id}/validate")
def validate_workflow(
    workflow_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.user_id == user.id)
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    errors = wf_service.validate_workflow(workflow.nodes or [], workflow.edges or [])
    return {"valid": len(errors) == 0, "errors": errors}
