import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from ..database import Base


class CallLog(Base):
    __tablename__ = "call_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(
        UUID(as_uuid=True), ForeignKey("call_campaigns.id"), nullable=False
    )
    twilio_call_sid = Column(String(100), nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    duration_sec = Column(Integer, nullable=True)
    outcome = Column(String(50), nullable=True)
    person_reached = Column(String(50), nullable=True)
    transcript = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    recording_url = Column(String(1000), nullable=True)
    next_steps = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    campaign = relationship("CallCampaign", back_populates="call_logs")
