"""API routes for entities — CRUD, merge, search."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.entity import Entity
from ..models.user import User
from ..schemas.entity import (
    EntityCreate,
    EntityMergeRequest,
    EntityResponse,
    EntityUpdate,
)
from ..services.entities.entity_service import EntityService

router = APIRouter(prefix="/entities", tags=["entities"])
_service = EntityService()


@router.post("", response_model=EntityResponse, status_code=201)
async def create_entity(
    body: EntityCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create an entity."""
    entity = await _service.create_entity(user.id, body.model_dump(), db)
    return entity


@router.get("", response_model=list[EntityResponse])
async def list_entities(
    entity_type: str | None = None,
    q: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List entities with optional type and search filters."""
    return await _service.search_entities(
        user_id=user.id,
        query=q,
        entity_type=entity_type,
        limit=limit,
        offset=offset,
        db=db,
    )


@router.get("/search", response_model=list[EntityResponse])
async def search_entities(
    q: str = Query(..., min_length=1),
    entity_type: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Search entities by name/description."""
    return await _service.search_entities(
        user_id=user.id,
        query=q,
        entity_type=entity_type,
        limit=limit,
        offset=offset,
        db=db,
    )


@router.get("/{entity_id}", response_model=EntityResponse)
def get_entity(
    entity_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get entity detail with canonical_data."""
    entity = (
        db.query(Entity)
        .filter(Entity.id == entity_id, Entity.user_id == user.id)
        .first()
    )
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


@router.put("/{entity_id}", response_model=EntityResponse)
async def update_entity(
    entity_id: UUID,
    body: EntityUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update entity data (merge, don't overwrite)."""
    entity = (
        db.query(Entity)
        .filter(Entity.id == entity_id, Entity.user_id == user.id)
        .first()
    )
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    return await _service.update_entity(entity_id, body.model_dump(exclude_unset=True), db)


@router.post("/merge", response_model=EntityResponse)
async def merge_entities(
    body: EntityMergeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Merge duplicate entities into one."""
    primary = (
        db.query(Entity)
        .filter(Entity.id == body.primary_id, Entity.user_id == user.id)
        .first()
    )
    if not primary:
        raise HTTPException(status_code=404, detail="Primary entity not found")

    return await _service.merge_entities(body.entity_ids, body.primary_id, db)
