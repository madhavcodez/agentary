from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, JSONB, UUID
from sqlalchemy.orm import relationship

from ..database import Base
from .enums import FailureCategory


class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True, index=True)
    mission_id = Column(UUID(as_uuid=True), ForeignKey("missions.id"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    report_type = Column(String(50), nullable=False, default="research_report")
    # Report uses domain-specific states (generating/ready/failed) rather than RunStatus.
    # These map to: generating=running, ready=completed, failed=failed.
    # This is intentional — reports have a simpler lifecycle than execution runs.
    status = Column(String(20), nullable=False, default="generating")
    content_markdown = Column(Text, nullable=True)
    content_html = Column(Text, nullable=True)
    sections = Column(JSON, nullable=True)
    executive_summary = Column(Text, nullable=True)
    methodology = Column(Text, nullable=True)
    sources = Column(JSON, nullable=True)
    charts = Column(JSON, nullable=True)
    structured_data = Column(JSON, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)
    format_config = Column(JSON, nullable=True)
    share_token = Column(String(255), nullable=True, unique=True, index=True)
    share_enabled = Column(Boolean, default=False)
    pdf_url = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Lifecycle state machine columns
    failure_category = Column(SAEnum(FailureCategory, name="failurecategory"), nullable=True)
    failure_message = Column(Text, nullable=True)
    state_transitions = Column(JSONB, default=list)
    correlation_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    user = relationship("User")
    project = relationship("Project")
    mission = relationship("Mission")
