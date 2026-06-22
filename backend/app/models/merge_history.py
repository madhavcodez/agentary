"""MergeHistory tracks entity merge operations to support undo."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from ..database import Base


class MergeHistory(Base):
    __tablename__ = "merge_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    primary_entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id"), nullable=False)
    # No FK: the merged entity is deleted after merge
    merged_entity_id = Column(UUID(as_uuid=True), nullable=False)
    merged_entity_snapshot = Column(JSONB, nullable=False)
    merged_aliases = Column(JSONB, default=list)
    merged_observations_count = Column(Integer, default=0)
    is_undone = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    project = relationship("Project")
    primary_entity = relationship("Entity")
