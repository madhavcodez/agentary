"""Scored listing output for the Pool Concierge vertical.

One row per (mission, listing) — the enriched, segmented, scored
candidate returned by ``run_pool_concierge_mission``. Polygons and pool
placement are stored verbatim as JSONB so downstream UI can render them
without re-running the pipeline.
"""
from __future__ import annotations

import uuid

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from ..database import Base


class PoolListing(Base):
    __tablename__ = "pool_listings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mission_id = Column(
        UUID(as_uuid=True),
        ForeignKey("missions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    listing_url = Column(Text, nullable=True)
    address = Column(String(500), nullable=False)
    # Audit fix (code-review HIGH #5): DTO and mission writes use
    # ``float`` for ``list_price`` but the column was declared as
    # ``Integer``, which silently truncated decimals on write. Use
    # ``Numeric(12, 2)`` to preserve currency precision.
    list_price = Column(Numeric(12, 2), nullable=True)
    lot_size_sqft = Column(Float, nullable=True)
    building_footprint_sqft = Column(Float, nullable=True)
    backyard_sqft = Column(Float, nullable=True)
    parcel_polygon = Column(JSONB, nullable=True)
    backyard_polygon = Column(JSONB, nullable=True)
    pool_placement = Column(JSONB, nullable=True)
    score = Column(Float, nullable=False, default=0.0)
    fit_reason = Column(Text, nullable=True)
    max_pool_size = Column(String(100), nullable=True)
    aerial_image_url = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    mission = relationship("Mission")
