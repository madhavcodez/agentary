from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from ..database import Base


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="draft", index=True)
    trigger_type = Column(String(20), nullable=False, default="manual")
    trigger_config = Column(JSONB, nullable=True)
    created_from = Column(String(30), nullable=False, default="visual_editor")
    template_id = Column(UUID(as_uuid=True), ForeignKey("workflow_templates.id"), nullable=True)
    nodes = Column(JSONB, nullable=False, default=list)
    edges = Column(JSONB, nullable=False, default=list)
    variables = Column(JSONB, nullable=False, default=dict)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    total_runs = Column(Integer, nullable=False, default=0)
    avg_duration_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    runs = relationship("WorkflowRun", back_populates="workflow", cascade="all, delete-orphan")
    template = relationship("WorkflowTemplate", foreign_keys=[template_id])
