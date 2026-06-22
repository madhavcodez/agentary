from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from ..database import Base


class DataSet(Base):
    __tablename__ = "datasets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    mission_id = Column(UUID(as_uuid=True), ForeignKey("missions.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    schema_definition = Column(JSONB, default=dict)  # {columns: [{name, type}]}
    row_count = Column(Integer, default=0)
    data = Column(JSONB)  # For small datasets
    file_path = Column(String(1024))  # For large datasets
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    project = relationship("Project", back_populates="datasets")
    rows = relationship("DataRow", back_populates="dataset", lazy="dynamic")


class DataRow(Base):
    __tablename__ = "data_rows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False, index=True)
    data = Column(JSONB, nullable=False)
    source_finding_id = Column(UUID(as_uuid=True), ForeignKey("findings.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    dataset = relationship("DataSet", back_populates="rows")
