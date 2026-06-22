"""API routes for entity collections — CRUD, add/remove entities, CSV export."""

from __future__ import annotations

import csv
import io
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.entity import Entity
from ..models.entity_collection import EntityCollection
from ..models.user import User
from ..schemas.entity_collection import (
    EntityCollectionAddRemove,
    EntityCollectionCreate,
    EntityCollectionResponse,
)
from ..services.entities.entity_service import EntityService

router = APIRouter(prefix="/entity-collections", tags=["entity-collections"])
_service = EntityService()


@router.post("", response_model=EntityCollectionResponse, status_code=201)
async def create_collection(
    body: EntityCollectionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new entity collection."""
    return await _service.create_collection(user.id, body.model_dump(), db)


@router.get("", response_model=list[EntityCollectionResponse])
def list_collections(
    project_id: UUID | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List collections for user, optionally filtered by project."""
    q = db.query(EntityCollection).filter(EntityCollection.user_id == user.id)
    if project_id:
        q = q.filter(EntityCollection.project_id == project_id)
    return q.order_by(EntityCollection.created_at.desc()).offset(offset).limit(limit).all()


@router.get("/{collection_id}", response_model=EntityCollectionResponse)
def get_collection(
    collection_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get collection detail."""
    collection = (
        db.query(EntityCollection)
        .filter(EntityCollection.id == collection_id, EntityCollection.user_id == user.id)
        .first()
    )
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@router.post("/{collection_id}/add", response_model=EntityCollectionResponse)
async def add_to_collection(
    collection_id: UUID,
    body: EntityCollectionAddRemove,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Add entities to a collection."""
    collection = (
        db.query(EntityCollection)
        .filter(EntityCollection.id == collection_id, EntityCollection.user_id == user.id)
        .first()
    )
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return await _service.add_to_collection(collection_id, body.entity_ids, db)


@router.post("/{collection_id}/remove", response_model=EntityCollectionResponse)
async def remove_from_collection(
    collection_id: UUID,
    body: EntityCollectionAddRemove,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Remove entities from a collection."""
    collection = (
        db.query(EntityCollection)
        .filter(EntityCollection.id == collection_id, EntityCollection.user_id == user.id)
        .first()
    )
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return await _service.remove_from_collection(collection_id, body.entity_ids, db)


@router.get("/{collection_id}/export/csv")
def export_collection_csv(
    collection_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Export collection entities as CSV."""
    collection = (
        db.query(EntityCollection)
        .filter(EntityCollection.id == collection_id, EntityCollection.user_id == user.id)
        .first()
    )
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    entities = db.query(Entity).filter(Entity.id.in_(collection.entity_ids or [])).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "type", "name", "description", "tags", "canonical_data"])
    for e in entities:
        writer.writerow(
            [
                str(e.id),
                e.entity_type,
                e.name,
                e.description or "",
                ";".join(e.tags or []),
                str(e.canonical_data or {}),
            ]
        )

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{collection.name}.csv"'},
    )
