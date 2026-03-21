import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from ..database import Base


class MissionResearchResult(Base):
    __tablename__ = "mission_research_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mission_id = Column(
        UUID(as_uuid=True), ForeignKey("missions.id"), nullable=False, index=True
    )
    crew_run_id = Column(
        UUID(as_uuid=True), ForeignKey("crew_runs.id"), nullable=True
    )
    title = Column(String(500), nullable=False)
    summary = Column(Text, nullable=True)
    sections = Column(
        JSONB, default=list
    )  # array of {title, content, finding_ids, chart_configs}
    structured_data = Column(JSONB, nullable=True)
    raw_data = Column(JSONB, nullable=True)
    sources_used = Column(Integer, nullable=False, default=0)
    findings_count = Column(Integer, nullable=False, default=0)
    confidence = Column(Float, nullable=True)
    methodology = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    mission = relationship("Mission", back_populates="mission_research_results")
    crew_run = relationship("CrewRun", back_populates="mission_research_results")
