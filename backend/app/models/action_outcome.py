from __future__ import annotations

import enum
import uuid

from sqlalchemy import Column, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from ..database import Base


class OutcomeType(str, enum.Enum):
    success = "success"
    partial_success = "partial_success"
    failure = "failure"
    rejected_by_user = "rejected_by_user"
    no_effect = "no_effect"
    needs_followup = "needs_followup"


class ActionOutcome(Base):
    __tablename__ = "action_outcomes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_request_id = Column(
        UUID(as_uuid=True), ForeignKey("action_requests.id"), nullable=False, index=True
    )
    execution_id = Column(
        UUID(as_uuid=True), ForeignKey("action_executions.id"), nullable=True, index=True
    )
    outcome_type = Column(SAEnum(OutcomeType), nullable=False)
    impact = Column(JSONB, default=dict)
    feedback_signal_id = Column(UUID(as_uuid=True), ForeignKey("signals.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    action_request = relationship("ActionRequest", back_populates="outcomes")
    execution = relationship("ActionExecution", back_populates="outcomes")
    feedback_signal = relationship("Signal")
