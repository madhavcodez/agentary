"""STORM phase 1: research_outlines table for pre-writing artifact.

Revision ID: e1a5c2b8f301
Revises: d128470fad95
Create Date: 2026-04-14 16:00:00.000000

Adds the pre-writing artifact produced by the STORM methodology
(perspective miner + question generator + outline planner). One row
per (mission, version).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e1a5c2b8f301"
down_revision: Union[str, None] = "d128470fad95"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "research_outlines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("perspectives", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("question_matrix", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("sections", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["mission_id"], ["missions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "mission_id", "version", name="uq_research_outlines_mission_version"
        ),
    )
    op.create_index(
        op.f("ix_research_outlines_mission_id"),
        "research_outlines",
        ["mission_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_research_outlines_mission_id"), table_name="research_outlines")
    op.drop_table("research_outlines")
