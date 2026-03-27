import uuid

from sqlalchemy import Column, DateTime, Enum as SAEnum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from ..database import Base
from .enums import FailureCategory, RunStatus


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    status = Column(SAEnum(RunStatus, name="runstatus", create_type=False), nullable=False, default=RunStatus.created)
    trigger_type = Column(String(20), nullable=False, default="manual")
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    node_results = Column(JSONB, nullable=False, default=dict)
    output_data = Column(JSONB, nullable=True)
    findings_generated = Column(Integer, nullable=False, default=0)
    error = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Lifecycle state machine columns
    failure_category = Column(SAEnum(FailureCategory, name="failurecategory"), nullable=True)
    failure_message = Column(Text, nullable=True)
    state_transitions = Column(JSONB, default=list)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    correlation_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    idempotency_key = Column(String(255), nullable=True, unique=True)

    workflow = relationship("Workflow", back_populates="runs")
