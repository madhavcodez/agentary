"""API routes for expert agents."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_session
from ..deps import get_current_user
from ..models.expert_agent import ExpertAgent
from ..models.user import User
from ..services.crews.expert_registry import create_custom_expert, seed_builtin_experts

router = APIRouter(prefix="/api/experts", tags=["experts"])


class ExpertCreate(BaseModel):
    name: str = Field(max_length=255)
    slug: str = Field(max_length=100)
    description: str | None = None
    specialty: str = "web_researcher"
    system_prompt: str
    tools: list[str] = []
    model_config_data: dict[str, Any] | None = Field(None, alias="model_config")
    icon: str = "\U0001f916"
    color: str = "#6B7280"


class ExpertUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    tools: list[str] | None = None
    model_config_data: dict[str, Any] | None = Field(None, alias="model_config")
    icon: str | None = None
    color: str | None = None
    is_active: bool | None = None


def _expert_to_dict(e: ExpertAgent) -> dict[str, Any]:
    return {
        "id": str(e.id),
        "slug": e.slug,
        "name": e.name,
        "description": e.description,
        "specialty": e.specialty.value if e.specialty else None,
        "system_prompt": e.system_prompt,
        "tools": e.tools or [],
        "model_config": e.model_config_json or {},
        "icon": e.icon,
        "color": e.color,
        "is_system": e.is_system,
        "is_active": e.is_active,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


@router.get("/")
async def list_experts(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """List all available expert agents (system + user custom)."""
    experts = (
        db.query(ExpertAgent)
        .filter(ExpertAgent.is_active.is_(True))
        .order_by(ExpertAgent.is_system.desc(), ExpertAgent.name)
        .all()
    )

    return {
        "total": len(experts),
        "items": [_expert_to_dict(e) for e in experts],
    }


@router.get("/{slug}")
async def get_expert(
    slug: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Get a specific expert by slug."""
    expert = db.query(ExpertAgent).filter_by(slug=slug, is_active=True).first()
    if not expert:
        raise HTTPException(404, "Expert not found")
    return _expert_to_dict(expert)


@router.post("/")
async def create_expert(
    body: ExpertCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Create a custom expert agent."""
    existing = db.query(ExpertAgent).filter_by(slug=body.slug).first()
    if existing:
        raise HTTPException(409, f"Expert with slug '{body.slug}' already exists")

    data = {
        "name": body.name,
        "slug": body.slug,
        "description": body.description,
        "specialty": body.specialty,
        "system_prompt": body.system_prompt,
        "tools": body.tools,
        "model_config": body.model_config_data or {"model": "gemini-2.5-flash", "temperature": 0.3, "max_tokens": 8192},
        "icon": body.icon,
        "color": body.color,
    }
    expert = await create_custom_expert(user.id, data, db)
    return _expert_to_dict(expert)


@router.put("/{expert_id}")
async def update_expert(
    expert_id: str,
    body: ExpertUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Update a custom expert agent. System agents cannot be modified."""
    expert = db.query(ExpertAgent).filter_by(id=uuid.UUID(expert_id)).first()
    if not expert:
        raise HTTPException(404, "Expert not found")
    if expert.is_system:
        raise HTTPException(403, "Cannot modify system expert agents")

    if body.name is not None:
        expert.name = body.name
    if body.description is not None:
        expert.description = body.description
    if body.system_prompt is not None:
        expert.system_prompt = body.system_prompt
    if body.tools is not None:
        expert.tools = body.tools
    if body.model_config_data is not None:
        expert.model_config_json = body.model_config_data
    if body.icon is not None:
        expert.icon = body.icon
    if body.color is not None:
        expert.color = body.color
    if body.is_active is not None:
        expert.is_active = body.is_active

    db.commit()
    db.refresh(expert)
    return _expert_to_dict(expert)


@router.post("/seed")
async def seed_experts(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Seed all 8 built-in expert agents."""
    experts = seed_builtin_experts(db)
    return {
        "seeded": len(experts),
        "experts": [{"slug": e.slug, "name": e.name} for e in experts],
    }
