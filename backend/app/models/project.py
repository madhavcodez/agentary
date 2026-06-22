from __future__ import annotations

import enum
import uuid

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..database import Base


class ProjectStatus(str, enum.Enum):
    active = "active"
    archived = "archived"
    completed = "completed"


class ProjectType(str, enum.Enum):
    market_research = "market_research"
    competitive_intel = "competitive_intel"
    due_diligence = "due_diligence"
    data_extraction = "data_extraction"
    real_estate = "real_estate"
    local_business = "local_business"
    custom = "custom"


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(SAEnum(ProjectStatus), default=ProjectStatus.active, nullable=False)
    project_type = Column(SAEnum(ProjectType), default=ProjectType.custom, nullable=False)
    domain_context = Column(Text)
    knowledge_base_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_bases.id"), nullable=True)
    default_workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=True)
    total_missions = Column(Integer, default=0, nullable=False)
    total_findings = Column(Integer, default=0, nullable=False)
    total_calls_made = Column(Integer, default=0, nullable=False)
    total_reports_generated = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    missions = relationship("Mission", back_populates="project", lazy="dynamic")
    findings = relationship("Finding", back_populates="project", lazy="dynamic")
    reports = relationship("Report", back_populates="project", lazy="dynamic")
    monitors = relationship("Monitor", back_populates="project", lazy="dynamic")
    datasets = relationship("DataSet", back_populates="project", lazy="dynamic")
    voice_extractions = relationship("VoiceExtraction", back_populates="project", lazy="dynamic")
    audit_logs = relationship("AuditLog", back_populates="project", lazy="dynamic")
