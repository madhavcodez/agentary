from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from ..database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True, index=True)
    mission_id = Column(UUID(as_uuid=True), ForeignKey("missions.id"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    report_type = Column(String(50), nullable=False, default="research_report")
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

    user = relationship("User", backref="reports")
    project = relationship("Project", backref="reports")
    mission = relationship("Mission", backref="reports")
