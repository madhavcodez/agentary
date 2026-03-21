"""API routes for voice extraction templates."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas.voice import TemplateListResponse, TemplateResponse
from ..services.voice.templates import (
    BUILT_IN_TEMPLATES,
    get_template_by_name,
    list_templates,
)

router = APIRouter(prefix="/voice/templates", tags=["voice-templates"])


@router.get("", response_model=TemplateListResponse)
def list_all_templates():
    """List all available extraction templates."""
    return TemplateListResponse(templates=list_templates())


@router.get("/{name}")
def get_template(name: str):
    """Get a specific template by name with full schema."""
    template = get_template_by_name(name)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{name}' not found")
    return template
