"""API routes for entity aliases — CRUD."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.entity import Entity
from ..models.entity_alias import AliasType, EntityAlias
from ..models.user import User
from ..schemas.intelligence import EntityAliasCreate, EntityAliasResponse

router = APIRouter(prefix="/api/entities", tags=["entity-aliases"])


@router.post("/{entity_id}/aliases", response_model=EntityAliasResponse, status_code=201)
def add_alias(
    entity_id: UUID,
    body: EntityAliasCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Add an alias to an entity."""
    entity = (
        db.query(Entity)
        .filter(Entity.id == entity_id, Entity.user_id == user.id)
        .first()
    )
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    alias = EntityAlias(
        entity_id=entity_id,
        alias_type=AliasType(body.alias_type),
        alias_value=body.alias_value,
        source_name=body.source_name,
        confidence=body.confidence,
    )
    db.add(alias)
    db.commit()
    db.refresh(alias)
    return alias


@router.get("/{entity_id}/aliases", response_model=list[EntityAliasResponse])
def list_aliases(
    entity_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all aliases for an entity."""
    entity = (
        db.query(Entity)
        .filter(Entity.id == entity_id, Entity.user_id == user.id)
        .first()
    )
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    return (
        db.query(EntityAlias)
        .filter(EntityAlias.entity_id == entity_id)
        .order_by(EntityAlias.created_at.desc())
        .all()
    )


@router.delete("/{entity_id}/aliases/{alias_id}", status_code=204)
def remove_alias(
    entity_id: UUID,
    alias_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Remove an alias from an entity."""
    entity = (
        db.query(Entity)
        .filter(Entity.id == entity_id, Entity.user_id == user.id)
        .first()
    )
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    alias = (
        db.query(EntityAlias)
        .filter(EntityAlias.id == alias_id, EntityAlias.entity_id == entity_id)
        .first()
    )
    if not alias:
        raise HTTPException(status_code=404, detail="Alias not found")

    db.delete(alias)
    db.commit()
