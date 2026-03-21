"""Entity management service with deduplication, merging, and search."""

from __future__ import annotations

import logging
import re
from typing import Any
from uuid import UUID

from rapidfuzz import fuzz
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ...models.entity import Entity
from ...models.entity_collection import EntityCollection

logger = logging.getLogger(__name__)

# Fuzzy match threshold for dedup
_MATCH_THRESHOLD = 85


def _normalize_address(address: str) -> str:
    """Normalize an address for comparison."""
    addr = address.lower().strip()
    addr = re.sub(r"\b(street|st\.?)\b", "st", addr)
    addr = re.sub(r"\b(avenue|ave\.?)\b", "ave", addr)
    addr = re.sub(r"\b(boulevard|blvd\.?)\b", "blvd", addr)
    addr = re.sub(r"\b(drive|dr\.?)\b", "dr", addr)
    addr = re.sub(r"\b(road|rd\.?)\b", "rd", addr)
    addr = re.sub(r"\b(lane|ln\.?)\b", "ln", addr)
    addr = re.sub(r"\b(suite|ste\.?)\b", "ste", addr)
    addr = re.sub(r"[#.,]", "", addr)
    addr = re.sub(r"\s+", " ", addr)
    return addr


def _merge_dicts(existing: dict, new: dict) -> dict:
    """Merge new data into existing, without overwriting non-null values."""
    merged = dict(existing)
    for key, value in new.items():
        if value is not None and (key not in merged or merged[key] is None):
            merged[key] = value
    return merged


class EntityService:
    """Service for creating, deduplicating, merging, and searching entities."""

    async def create_entity(
        self, user_id: UUID, data: dict[str, Any], db: Session
    ) -> Entity:
        """Create a new entity."""
        entity = Entity(
            user_id=user_id,
            entity_type=data["entity_type"],
            name=data["name"],
            description=data.get("description"),
            canonical_data=data.get("canonical_data", {}),
            aliases=data.get("aliases", []),
            source_urls=data.get("source_urls", []),
            tags=data.get("tags", []),
        )
        db.add(entity)
        db.commit()
        db.refresh(entity)
        return entity

    async def find_or_create(
        self,
        user_id: UUID,
        entity_type: str,
        identifiers: dict[str, Any],
        db: Session,
    ) -> Entity:
        """Find existing entity by matching identifiers, or create new.

        Match logic:
        - person: email OR (name + company)
        - company: domain OR name
        - property: address (normalized)
        - business: phone OR (name + address)
        - location: name
        """
        existing = self._find_match(user_id, entity_type, identifiers, db)
        if existing:
            # Merge any new canonical_data
            if "canonical_data" in identifiers:
                merged = _merge_dicts(
                    existing.canonical_data or {}, identifiers["canonical_data"]
                )
                existing.canonical_data = merged
                db.commit()
                db.refresh(existing)
            return existing

        # Create new
        name = identifiers.get("name", identifiers.get("full_name", "Unknown"))
        return await self.create_entity(
            user_id=user_id,
            data={
                "entity_type": entity_type,
                "name": name,
                "description": identifiers.get("description"),
                "canonical_data": identifiers.get("canonical_data", identifiers),
                "aliases": identifiers.get("aliases", []),
                "source_urls": identifiers.get("source_urls", []),
                "tags": identifiers.get("tags", []),
            },
            db=db,
        )

    def _find_match(
        self,
        user_id: UUID,
        entity_type: str,
        identifiers: dict[str, Any],
        db: Session,
    ) -> Entity | None:
        """Find an existing entity matching the given identifiers."""
        base_query = db.query(Entity).filter(
            Entity.user_id == user_id, Entity.entity_type == entity_type
        )

        if entity_type == "person":
            return self._match_person(base_query, identifiers)
        elif entity_type == "company":
            return self._match_company(base_query, identifiers)
        elif entity_type == "property":
            return self._match_property(base_query, identifiers)
        elif entity_type == "business":
            return self._match_business(base_query, identifiers)
        elif entity_type == "location":
            return self._match_location(base_query, identifiers)
        else:
            # Generic: match by exact name
            name = identifiers.get("name", "")
            if name:
                return base_query.filter(Entity.name == name).first()
        return None

    def _match_person(self, query, identifiers: dict) -> Entity | None:
        email = identifiers.get("email")
        if email:
            candidates = query.all()
            for c in candidates:
                cd = c.canonical_data or {}
                if cd.get("email", "").lower() == email.lower():
                    return c

        name = identifiers.get("name") or identifiers.get("full_name")
        company = identifiers.get("company")
        if name and company:
            candidates = query.all()
            for c in candidates:
                cd = c.canonical_data or {}
                if (
                    fuzz.ratio(c.name.lower(), name.lower()) >= _MATCH_THRESHOLD
                    and fuzz.ratio(
                        (cd.get("company") or "").lower(), company.lower()
                    )
                    >= _MATCH_THRESHOLD
                ):
                    return c
        return None

    def _match_company(self, query, identifiers: dict) -> Entity | None:
        domain = identifiers.get("domain")
        if domain:
            candidates = query.all()
            for c in candidates:
                cd = c.canonical_data or {}
                if (cd.get("domain") or "").lower() == domain.lower():
                    return c

        name = identifiers.get("name")
        if name:
            candidates = query.all()
            for c in candidates:
                if fuzz.ratio(c.name.lower(), name.lower()) >= _MATCH_THRESHOLD:
                    return c
        return None

    def _match_property(self, query, identifiers: dict) -> Entity | None:
        address = identifiers.get("address")
        if not address:
            return None
        normalized = _normalize_address(address)
        candidates = query.all()
        for c in candidates:
            cd = c.canonical_data or {}
            existing_addr = cd.get("address", c.name)
            if fuzz.ratio(_normalize_address(existing_addr), normalized) >= 90:
                return c
        return None

    def _match_business(self, query, identifiers: dict) -> Entity | None:
        phone = identifiers.get("phone")
        if phone:
            stripped = re.sub(r"[^\d]", "", phone)
            candidates = query.all()
            for c in candidates:
                cd = c.canonical_data or {}
                existing_phone = re.sub(r"[^\d]", "", cd.get("phone", ""))
                if existing_phone and existing_phone == stripped:
                    return c

        name = identifiers.get("name")
        address = identifiers.get("address")
        if name and address:
            candidates = query.all()
            for c in candidates:
                cd = c.canonical_data or {}
                if fuzz.ratio(c.name.lower(), name.lower()) >= _MATCH_THRESHOLD:
                    existing_addr = cd.get("address", "")
                    if existing_addr and fuzz.ratio(
                        _normalize_address(existing_addr),
                        _normalize_address(address),
                    ) >= 80:
                        return c
        return None

    def _match_location(self, query, identifiers: dict) -> Entity | None:
        name = identifiers.get("name")
        if name:
            candidates = query.all()
            for c in candidates:
                if fuzz.ratio(c.name.lower(), name.lower()) >= _MATCH_THRESHOLD:
                    return c
        return None

    async def update_entity(
        self, entity_id: UUID, data: dict[str, Any], db: Session
    ) -> Entity:
        """Merge new data into canonical_data (don't overwrite, merge)."""
        entity = db.query(Entity).filter(Entity.id == entity_id).first()
        if not entity:
            raise ValueError(f"Entity {entity_id} not found")

        if "name" in data and data["name"]:
            entity.name = data["name"]
        if "description" in data:
            entity.description = data["description"]
        if "canonical_data" in data and data["canonical_data"]:
            entity.canonical_data = _merge_dicts(
                entity.canonical_data or {}, data["canonical_data"]
            )
        if "aliases" in data:
            existing = set(entity.aliases or [])
            existing.update(data["aliases"])
            entity.aliases = list(existing)
        if "source_urls" in data:
            existing = set(entity.source_urls or [])
            existing.update(data["source_urls"])
            entity.source_urls = list(existing)
        if "tags" in data:
            existing = set(entity.tags or [])
            existing.update(data["tags"])
            entity.tags = list(existing)

        db.commit()
        db.refresh(entity)
        return entity

    async def merge_entities(
        self, entity_ids: list[UUID], primary_id: UUID, db: Session
    ) -> Entity:
        """Merge duplicates into one. Combine canonical_data, aliases, source_urls."""
        primary = db.query(Entity).filter(Entity.id == primary_id).first()
        if not primary:
            raise ValueError(f"Primary entity {primary_id} not found")

        others = (
            db.query(Entity)
            .filter(Entity.id.in_(entity_ids), Entity.id != primary_id)
            .all()
        )

        all_aliases = set(primary.aliases or [])
        all_source_urls = set(primary.source_urls or [])
        all_tags = set(primary.tags or [])
        merged_data = dict(primary.canonical_data or {})

        for other in others:
            all_aliases.add(other.name)
            all_aliases.update(other.aliases or [])
            all_source_urls.update(other.source_urls or [])
            all_tags.update(other.tags or [])
            merged_data = _merge_dicts(merged_data, other.canonical_data or {})
            db.delete(other)

        primary.canonical_data = merged_data
        primary.aliases = list(all_aliases)
        primary.source_urls = list(all_source_urls)
        primary.tags = list(all_tags)

        db.commit()
        db.refresh(primary)
        return primary

    async def search_entities(
        self,
        user_id: UUID,
        query: str | None = None,
        entity_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
        db: Session = None,
    ) -> list[Entity]:
        """Full-text search on entity name and description."""
        q = db.query(Entity).filter(Entity.user_id == user_id)

        if entity_type:
            q = q.filter(Entity.entity_type == entity_type)

        if query:
            pattern = f"%{query}%"
            q = q.filter(
                or_(
                    Entity.name.ilike(pattern),
                    Entity.description.ilike(pattern),
                )
            )

        return q.order_by(Entity.created_at.desc()).offset(offset).limit(limit).all()

    async def create_collection(
        self,
        user_id: UUID,
        data: dict[str, Any],
        db: Session,
    ) -> EntityCollection:
        """Create an entity collection."""
        collection = EntityCollection(
            user_id=user_id,
            project_id=data.get("project_id"),
            name=data["name"],
            description=data.get("description"),
            entity_type=data.get("entity_type"),
            entity_ids=[],
            count=0,
        )
        db.add(collection)
        db.commit()
        db.refresh(collection)
        return collection

    async def add_to_collection(
        self, collection_id: UUID, entity_ids: list[UUID], db: Session
    ) -> EntityCollection:
        """Add entities to a collection."""
        collection = (
            db.query(EntityCollection)
            .filter(EntityCollection.id == collection_id)
            .first()
        )
        if not collection:
            raise ValueError(f"Collection {collection_id} not found")

        existing = set(collection.entity_ids or [])
        existing.update(entity_ids)
        collection.entity_ids = list(existing)
        collection.count = len(collection.entity_ids)
        db.commit()
        db.refresh(collection)
        return collection

    async def remove_from_collection(
        self, collection_id: UUID, entity_ids: list[UUID], db: Session
    ) -> EntityCollection:
        """Remove entities from a collection."""
        collection = (
            db.query(EntityCollection)
            .filter(EntityCollection.id == collection_id)
            .first()
        )
        if not collection:
            raise ValueError(f"Collection {collection_id} not found")

        remaining = [eid for eid in (collection.entity_ids or []) if eid not in entity_ids]
        collection.entity_ids = remaining
        collection.count = len(remaining)
        db.commit()
        db.refresh(collection)
        return collection
