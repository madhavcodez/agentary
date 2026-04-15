"""STORM phase 4: storm_runs telemetry table + missions.storm_enabled flag.

Revision ID: e3c7e5daf503
Revises: e2b6d4c9a402
Create Date: 2026-04-14 16:10:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e3c7e5daf503"
down_revision: Union[str, None] = "e2b6d4c9a402"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "missions",
        sa.Column("storm_enabled", sa.Boolean(), nullable=True),
    )

    op.create_table(
        "storm_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("crew_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("outline_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("fallback_reason", sa.String(length=255), nullable=True),
        sa.Column("perspectives_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("questions_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sections_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "sections_with_evidence", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("citations_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "refinement_passes", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("flash_calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pro_calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["crew_run_id"], ["crew_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mission_id"], ["missions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["outline_id"], ["research_outlines.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_storm_runs_crew_run_id"),
        "storm_runs",
        ["crew_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_storm_runs_mission_id"),
        "storm_runs",
        ["mission_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_storm_runs_mission_id"), table_name="storm_runs")
    op.drop_index(op.f("ix_storm_runs_crew_run_id"), table_name="storm_runs")
    op.drop_table("storm_runs")
    op.drop_column("missions", "storm_enabled")
