import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID

from ..database import Base


class ExtractionTemplate(Base):
    __tablename__ = "extraction_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )

    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(
        String(50), nullable=False, default="custom"
    )  # business_info | pricing | availability | hours | services | opinions | screening | custom

    extraction_fields = Column(
        JSON, nullable=False
    )  # [{field_name, field_type, question_template, required, validation}]
    persona_template = Column(JSON, nullable=True)  # default persona for this template

    is_system = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
