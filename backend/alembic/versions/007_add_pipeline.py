"""Add pipeline stage columns and transitions table

Revision ID: 007
Revises: 006
Create Date: 2026-03-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- matches: add pipeline columns --
    op.add_column(
        "matches",
        sa.Column("pipeline_stage", sa.String(20), nullable=True),
    )
    op.add_column(
        "matches",
        sa.Column("stage_changed_at", sa.DateTime(), nullable=True),
    )

    # Backfill existing rows to "lead"
    op.execute(
        sa.text("UPDATE matches SET pipeline_stage = 'lead' WHERE pipeline_stage IS NULL")
    )

    # Make NOT NULL after backfill
    op.alter_column("matches", "pipeline_stage", nullable=False)

    op.create_index("ix_matches_pipeline_stage", "matches", ["pipeline_stage"])

    # -- pipeline_transitions table --
    op.create_table(
        "pipeline_transitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "match_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("matches.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("from_stage", sa.String(20), nullable=False),
        sa.Column("to_stage", sa.String(20), nullable=False),
        sa.Column("trigger", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("pipeline_transitions")
    op.drop_index("ix_matches_pipeline_stage", table_name="matches")
    op.drop_column("matches", "stage_changed_at")
    op.drop_column("matches", "pipeline_stage")
