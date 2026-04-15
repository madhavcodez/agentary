"""Pool Concierge Stream C: contractor_reports table.

Revision ID: f2e9d8c7b605
Revises: f1d8e7c6b504
Create Date: 2026-04-15 01:30:00.000000

Adds ``contractor_reports`` — one row per contractor pipeline run for a
given ``pool_listing``. Holds the top-N ranked quotes as JSONB alongside
progress counters (discovered / verified / quoted).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f2e9d8c7b605"
down_revision: Union[str, None] = "f1d8e7c6b504"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_STATUS_ENUM = sa.Enum(
    "pending",
    "quoting",
    "ready",
    "failed",
    name="contractorreportstatus",
)


def upgrade() -> None:
    _STATUS_ENUM.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "contractor_reports",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "pool_listing_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "status",
            _STATUS_ENUM,
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "discovery_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "verified_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "quote_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "top_quotes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["pool_listing_id"],
            ["pool_listings.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_contractor_reports_pool_listing_id"),
        "contractor_reports",
        ["pool_listing_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_contractor_reports_pool_listing_id"),
        table_name="contractor_reports",
    )
    op.drop_table("contractor_reports")
    _STATUS_ENUM.drop(op.get_bind(), checkfirst=True)
