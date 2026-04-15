"""Pool Concierge phase 1: pool_listings table.

Revision ID: f1d8e7c6b504
Revises: e3c7e5daf503
Create Date: 2026-04-15 01:05:00.000000

Adds ``pool_listings`` — one row per scored Pool Concierge candidate
produced by ``run_pool_concierge_mission``. Polygons and the placement
rectangle are stored as JSONB for direct rendering on the UI.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f1d8e7c6b504"
down_revision: Union[str, None] = "e3c7e5daf503"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pool_listings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "mission_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("listing_url", sa.Text(), nullable=True),
        sa.Column("address", sa.String(length=500), nullable=False),
        # Audit fix (code-review HIGH #5): ``list_price`` arrives as a
        # float from mission writes; use ``Numeric(12, 2)`` to avoid the
        # silent truncation that ``Integer`` would cause.
        sa.Column(
            "list_price", sa.Numeric(precision=12, scale=2), nullable=True
        ),
        sa.Column("lot_size_sqft", sa.Float(), nullable=True),
        sa.Column("building_footprint_sqft", sa.Float(), nullable=True),
        sa.Column("backyard_sqft", sa.Float(), nullable=True),
        sa.Column(
            "parcel_polygon",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "backyard_polygon",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "pool_placement",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "score",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0.0"),
        ),
        sa.Column("fit_reason", sa.Text(), nullable=True),
        sa.Column("max_pool_size", sa.String(length=100), nullable=True),
        sa.Column("aerial_image_url", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["mission_id"], ["missions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_pool_listings_mission_id"),
        "pool_listings",
        ["mission_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_pool_listings_mission_id"),
        table_name="pool_listings",
    )
    op.drop_table("pool_listings")
