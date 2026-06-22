"""API routes for entity relationships — create and list."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.entity import Entity
from ..models.entity_relationship import EntityRelationship, RelationshipType
from ..models.user import User
from ..schemas.intelligence import EntityRelationshipCreate, EntityRelationshipResponse

router = APIRouter(tags=["entity-relationships"])


@router.post(
    "/api/entity-relationships", response_model=EntityRelationshipResponse, status_code=201
)
def create_relationship(
    body: EntityRelationshipCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a relationship between two entities."""
    from_entity = (
        db.query(Entity).filter(Entity.id == body.from_entity_id, Entity.user_id == user.id).first()
    )
    if not from_entity:
        raise HTTPException(status_code=404, detail="Source entity not found")

    to_entity = (
        db.query(Entity).filter(Entity.id == body.to_entity_id, Entity.user_id == user.id).first()
    )
    if not to_entity:
        raise HTTPException(status_code=404, detail="Target entity not found")

    rel = EntityRelationship(
        project_id=body.project_id,
        from_entity_id=body.from_entity_id,
        to_entity_id=body.to_entity_id,
        relationship_type=RelationshipType(body.relationship_type),
        properties=body.properties or {},
        confidence=body.confidence,
        source_id=body.source_id,
    )
    db.add(rel)
    db.commit()
    db.refresh(rel)
    return rel


@router.get(
    "/api/entities/{entity_id}/relationships",
    response_model=list[EntityRelationshipResponse],
)
def list_entity_relationships(
    entity_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """List all relationships for an entity (both directions)."""
    return (
        db.query(EntityRelationship)
        .filter(
            or_(
                EntityRelationship.from_entity_id == entity_id,
                EntityRelationship.to_entity_id == entity_id,
            )
        )
        .order_by(EntityRelationship.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
