from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from ..database import Base


class ActionType(str, enum.Enum):
    update_status = "update_status"
    send_alert = "send_alert"
    trigger_workflow = "trigger_workflow"
    trigger_monitor = "trigger_monitor"
    create_task = "create_task"
    generate_report = "generate_report"
    send_digest = "send_digest"
    queue_call = "queue_call"
    merge_entities = "merge_entities"
    escalate = "escalate"
    custom = "custom"


class ActionRequestStatus(str, enum.Enum):
    pending_approval = "pending_approval"
    approved = "approved"
    rejected = "rejected"
    executing = "executing"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"
    expired = "expired"


class ActionRequest(Base):
    __tablename__ = "action_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    recommendation_id = Column(UUID(as_uuid=True), ForeignKey("recommendations.id"), nullable=True, index=True)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    action_type = Column(SAEnum(ActionType), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    parameters = Column(JSONB, default=dict)
    confidence = Column(Float, default=1.0, nullable=False)
    priority = Column(String(20), default="medium", nullable=False)
    requires_approval = Column(Boolean, default=True, nullable=False)
    status = Column(SAEnum(ActionRequestStatus), default=ActionRequestStatus.pending_approval, nullable=False)
    state_transitions = Column(JSONB, default=list)
    policy_id = Column(UUID(as_uuid=True), ForeignKey("action_policies.id"), nullable=True)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    project = relationship("Project")
    recommendation = relationship("Recommendation")
    entity = relationship("Entity")
    executions = relationship("ActionExecution", back_populates="action_request")
    outcomes = relationship("ActionOutcome", back_populates="action_request")
