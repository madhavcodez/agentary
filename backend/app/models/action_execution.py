from __future__ import annotations

import enum
import uuid

from sqlalchemy import Column, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from ..database import Base


class ExecutorType(str, enum.Enum):
    system = "system"
    celery_worker = "celery_worker"
    external = "external"


class ExecutionStatus(str, enum.Enum):
    running = "running"
    completed = "completed"
    failed = "failed"
    rolled_back = "rolled_back"


class ActionExecution(Base):
    __tablename__ = "action_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_request_id = Column(
        UUID(as_uuid=True), ForeignKey("action_requests.id"), nullable=False, index=True
    )
    executor_type = Column(SAEnum(ExecutorType), default=ExecutorType.celery_worker, nullable=False)
    status = Column(SAEnum(ExecutionStatus), default=ExecutionStatus.running, nullable=False)
    result = Column(JSONB, default=dict)
    error = Column(JSONB, nullable=True)
    side_effects = Column(JSONB, default=list)  # what was changed, for rollback reference
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    action_request = relationship("ActionRequest", back_populates="executions")
    outcomes = relationship("ActionOutcome", back_populates="execution")
