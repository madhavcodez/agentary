"""Entity management service with deduplication, merging, and search."""

from __future__ import annotations

import logging
import re
from typing import Any
from uuid import UUID

from rapidfuzz import fuzz
from sqlalchemy import func as sa_func, or_
from sqlalchemy.orm import Session

from ...models.entity import Entity
from ...models.entity_alias import AliasType, EntityAlias
from ...models.entity_collection import EntityCollection
from ...models.entity_relationship import EntityRelationship
from ...models.insight import Insight
from ...models.observation import Observation
from ...models.recommendation import Recommendation

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
        if entity_type == "company":
            return self._match_company(base_query, identifiers)
        if entity_type == "property":
            return self._match_property(base_query, identifiers)
        if entity_type == "business":
            return self._match_business(base_query, identifiers)
        if entity_type == "location":
            return self._match_location(base_query, identifiers)
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

    # ── Alias-aware resolution (Epic 2.4) ──────────────────────────────

    def find_by_alias(
        self,
        alias_value: str,
        alias_type: AliasType | None = None,
        project_id: UUID | None = None,
        db: Session | None = None,
    ) -> Entity | None:
        """Find entity by any alias."""
        session = db or getattr(self, "_db", None)
        if session is None:
            raise ValueError("A database session is required")
        q = session.query(Entity).join(EntityAlias)
        q = q.filter(EntityAlias.alias_value == alias_value)
        if alias_type:
            q = q.filter(EntityAlias.alias_type == alias_type)
        if project_id:
            q = q.filter(Entity.project_id == project_id)
        return q.first()

    def find_or_create_with_aliases(
        self,
        name: str,
        entity_type: str,
        project_id: UUID,
        user_id: UUID,
        db: Session,
        aliases: list[dict] | None = None,
        properties: dict | None = None,
    ) -> tuple[Entity, bool]:
        """Find existing entity by name or aliases, or create new one.

        Returns (entity, is_new).
        """
        # 1. Exact name match
        existing = (
            db.query(Entity)
            .filter(Entity.name == name, Entity.project_id == project_id)
            .first()
        )
        if existing:
            return existing, False

        # 2. Check aliases
        if aliases:
            for alias in aliases:
                alias_type = (
                    AliasType(alias["type"]) if alias.get("type") else None
                )
                found = self.find_by_alias(
                    alias["value"], alias_type, project_id, db
                )
                if found:
                    return found, False

        # 3. Fuzzy name match (case-insensitive, strip whitespace)
        fuzzy = (
            db.query(Entity)
            .filter(
                sa_func.lower(sa_func.trim(Entity.name))
                == name.lower().strip(),
                Entity.project_id == project_id,
            )
            .first()
        )
        if fuzzy:
            return fuzzy, False

        # 4. Create new
        entity = Entity(
            name=name,
            entity_type=entity_type,
            project_id=project_id,
            user_id=user_id,
            properties=properties or {},
        )
        db.add(entity)
        db.flush()

        # Add provided aliases
        if aliases:
            for alias in aliases:
                a = EntityAlias(
                    entity_id=entity.id,
                    alias_type=AliasType(alias.get("type", "name_variant")),
                    alias_value=alias["value"],
                    source_name=alias.get("source"),
                    confidence=alias.get("confidence", 1.0),
                )
                db.add(a)

        # Also store the canonical name as an alias
        name_alias = EntityAlias(
            entity_id=entity.id,
            alias_type=AliasType.name_variant,
            alias_value=name,
            confidence=1.0,
        )
        db.add(name_alias)
        db.flush()

        return entity, True

    def get_merge_candidates(
        self, project_id: UUID, db: Session, min_confidence: float = 0.7
    ) -> list[dict]:
        """Find potential entity duplicates for review."""
        entities = (
            db.query(Entity)
            .filter(Entity.project_id == project_id)
            .all()
        )

        candidates: list[dict] = []
        seen: set[tuple[str, str]] = set()

        for i, e1 in enumerate(entities):
            for e2 in entities[i + 1 :]:
                if e1.entity_type != e2.entity_type:
                    continue
                pair_key = tuple(sorted([str(e1.id), str(e2.id)]))
                if pair_key in seen:
                    continue

                # Normalized name comparison
                n1 = e1.name.lower().strip()
                n2 = e2.name.lower().strip()

                confidence = 0.0
                if n1 == n2:
                    confidence = 1.0
                elif n1 in n2 or n2 in n1:
                    confidence = 0.8
                else:
                    words1 = set(n1.split())
                    words2 = set(n2.split())
                    overlap = len(words1 & words2)
                    total = max(len(words1), len(words2))
                    if total > 0 and overlap / total > 0.5:
                        confidence = 0.7

                if confidence >= min_confidence:
                    seen.add(pair_key)

                    def _type_val(t: Any) -> str:
                        return t.value if hasattr(t, "value") else str(t)

                    candidates.append(
                        {
                            "entity_a": {
                                "id": str(e1.id),
                                "name": e1.name,
                                "type": _type_val(e1.entity_type),
                            },
                            "entity_b": {
                                "id": str(e2.id),
                                "name": e2.name,
                                "type": _type_val(e2.entity_type),
                            },
                            "confidence": confidence,
                            "reason": "name_similarity",
                        }
                    )

        return sorted(candidates, key=lambda x: -x["confidence"])

    # ── Enhanced merge with undo support (Epic 2.4) ────────────────────

    async def merge_entities_enhanced(
        self,
        primary_id: UUID,
        secondary_id: UUID,
        user_id: UUID,
        project_id: UUID,
        db: Session,
    ) -> dict:
        """Merge secondary entity into primary, with snapshot for undo."""
        from ...models.merge_history import MergeHistory

        primary = db.query(Entity).filter(Entity.id == primary_id).first()
        if not primary:
            raise ValueError(f"Primary entity {primary_id} not found")
        secondary = db.query(Entity).filter(Entity.id == secondary_id).first()
        if not secondary:
            raise ValueError(f"Secondary entity {secondary_id} not found")

        # 1. Snapshot the secondary entity
        snapshot = {
            "name": secondary.name,
            "entity_type": (
                secondary.entity_type.value
                if hasattr(secondary.entity_type, "value")
                else str(secondary.entity_type)
            ),
            "description": secondary.description,
            "properties": secondary.properties or {},
            "tags": secondary.tags or [],
            "source_ids": secondary.source_ids or [],
            "confidence_score": secondary.confidence_score,
            "is_verified": secondary.is_verified,
            "project_id": str(secondary.project_id) if secondary.project_id else None,
            "user_id": str(secondary.user_id),
        }

        # 2. Collect aliases being transferred
        secondary_aliases = (
            db.query(EntityAlias)
            .filter(EntityAlias.entity_id == secondary_id)
            .all()
        )
        merged_aliases_data = [
            {
                "id": str(a.id),
                "alias_type": a.alias_type.value,
                "alias_value": a.alias_value,
                "source_name": a.source_name,
                "confidence": a.confidence,
            }
            for a in secondary_aliases
        ]

        # 3. Count observations to transfer
        obs_count = (
            db.query(Observation)
            .filter(Observation.entity_id == secondary_id)
            .count()
        )

        # 4. Transfer aliases
        for alias in secondary_aliases:
            alias.entity_id = primary_id
        db.flush()

        # 5. Transfer observations
        db.query(Observation).filter(
            Observation.entity_id == secondary_id
        ).update({"entity_id": primary_id}, synchronize_session="fetch")

        # 6. Transfer insights
        db.query(Insight).filter(
            Insight.entity_id == secondary_id
        ).update({"entity_id": primary_id}, synchronize_session="fetch")

        # 7. Transfer recommendations
        db.query(Recommendation).filter(
            Recommendation.entity_id == secondary_id
        ).update({"entity_id": primary_id}, synchronize_session="fetch")

        # 8. Transfer relationships
        db.query(EntityRelationship).filter(
            EntityRelationship.from_entity_id == secondary_id
        ).update({"from_entity_id": primary_id}, synchronize_session="fetch")
        db.query(EntityRelationship).filter(
            EntityRelationship.to_entity_id == secondary_id
        ).update({"to_entity_id": primary_id}, synchronize_session="fetch")

        # 9. Merge properties
        merged_props = _merge_dicts(
            primary.properties or {}, secondary.properties or {}
        )
        primary.properties = merged_props

        # 10. Create MergeHistory record
        merge_record = MergeHistory(
            project_id=project_id,
            user_id=user_id,
            primary_entity_id=primary_id,
            merged_entity_id=secondary_id,
            merged_entity_snapshot=snapshot,
            merged_aliases=merged_aliases_data,
            merged_observations_count=obs_count,
        )
        db.add(merge_record)

        # 11. Delete the secondary entity
        db.delete(secondary)
        db.flush()

        return {
            "primary_entity_id": str(primary_id),
            "merged_entity_id": str(secondary_id),
            "merge_id": str(merge_record.id),
            "aliases_transferred": len(merged_aliases_data),
            "observations_transferred": obs_count,
        }

    async def undo_merge(self, merge_id: UUID, db: Session) -> dict:
        """Undo a previous entity merge by restoring from snapshot."""
        from ...models.merge_history import MergeHistory

        record = (
            db.query(MergeHistory)
            .filter(MergeHistory.id == merge_id, MergeHistory.is_undone.is_(False))
            .first()
        )
        if not record:
            raise ValueError(f"Merge record {merge_id} not found or already undone")

        snapshot = record.merged_entity_snapshot

        # 1. Re-create the merged entity from snapshot
        restored = Entity(
            id=record.merged_entity_id,
            name=snapshot["name"],
            entity_type=snapshot["entity_type"],
            description=snapshot.get("description"),
            properties=snapshot.get("properties", {}),
            tags=snapshot.get("tags", []),
            source_ids=snapshot.get("source_ids", []),
            confidence_score=snapshot.get("confidence_score"),
            is_verified=snapshot.get("is_verified", False),
            project_id=record.project_id,
            user_id=UUID(snapshot["user_id"]),
        )
        db.add(restored)
        db.flush()

        # 2. Transfer back aliases that came from the merged entity
        alias_ids = [a["id"] for a in (record.merged_aliases or [])]
        if alias_ids:
            db.query(EntityAlias).filter(
                EntityAlias.id.in_([UUID(aid) for aid in alias_ids])
            ).update(
                {"entity_id": record.merged_entity_id},
                synchronize_session="fetch",
            )

        # 3. Mark merge as undone
        record.is_undone = True
        db.flush()

        return {
            "merge_id": str(merge_id),
            "restored_entity_id": str(record.merged_entity_id),
            "restored_entity_name": snapshot["name"],
            "aliases_restored": len(alias_ids),
        }

    async def update_entity(
        self, entity_id: UUID, data: dict[str, Any], db: Session
    ) -> Entity:
        """Merge new data into canonical_data (don't overwrite, merge)."""
        entity = db.query(Entity).filter(Entity.id == entity_id).first()
        if not entity:
            raise ValueError(f"Entity {entity_id} not found")

        if data.get("name"):
            entity.name = data["name"]
        if "description" in data:
            entity.description = data["description"]
        if data.get("canonical_data"):
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
