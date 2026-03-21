from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.user import User
from ..models.workflow_template import WorkflowTemplate
from ..schemas.workflow import WorkflowTemplateCreate, WorkflowTemplateResponse

router = APIRouter(prefix="/workflow-templates", tags=["workflow-templates"])


@router.get("", response_model=list[WorkflowTemplateResponse])
def list_templates(
    category: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List system templates + user's custom templates."""
    query = db.query(WorkflowTemplate).filter(
        or_(
            WorkflowTemplate.is_system == True,  # noqa: E712
            WorkflowTemplate.is_public == True,  # noqa: E712
            WorkflowTemplate.user_id == user.id,
        )
    )
    if category:
        query = query.filter(WorkflowTemplate.category == category)

    return query.order_by(WorkflowTemplate.install_count.desc()).all()


@router.get("/{template_id}", response_model=WorkflowTemplateResponse)
def get_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a template with its variables schema."""
    template = (
        db.query(WorkflowTemplate)
        .filter(
            WorkflowTemplate.id == template_id,
            or_(
                WorkflowTemplate.is_system == True,  # noqa: E712
                WorkflowTemplate.is_public == True,  # noqa: E712
                WorkflowTemplate.user_id == user.id,
            ),
        )
        .first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.post("", response_model=WorkflowTemplateResponse, status_code=201)
def create_template(
    body: WorkflowTemplateCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a custom template from an existing workflow or manually."""
    template = WorkflowTemplate(
        user_id=user.id,
        name=body.name,
        description=body.description,
        category=body.category,
        tags=body.tags,
        nodes_template=body.nodes_template,
        edges_template=body.edges_template,
        variables_schema=body.variables_schema,
        is_system=False,
        is_public=False,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template
