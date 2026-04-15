"""Pool Concierge Stream E: pool_pipeline_runs + pool_saved_searches.

Revision ID: f3fa0e9d8a06
Revises: f2e9d8c7b605
Create Date: 2026-04-15 01:45:00.000000

Adds:

* ``pool_pipeline_runs`` — one row per end-to-end pipeline invocation
  (discovery -> scoring -> contractor quotes -> permit checklists). The
  status enum mirrors the stages the Telegram digest shows the user.
* ``pool_saved_searches`` — standing per-user ZIP/radius/budget records
  the morning cron iterates over.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f3fa0e9d8a06"
down_revision: Union[str, None] = "f2e9d8c7b605"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_RUN_STATUS_ENUM = sa.Enum(
    "pending",
    "discovering",
    "scoring",
    "contractor_quoting",
    "ready",
    "failed",
    name="poolpipelinerunstatus",
)


def upgrade() -> None:
    _RUN_STATUS_ENUM.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "pool_pipeline_runs",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("zipcode", sa.String(length=10), nullable=False),
        sa.Column(
            "status",
            _RUN_STATUS_ENUM,
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "total_listings",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "ready_listings",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "telegram_message_id", sa.String(length=64), nullable=True
        ),
        sa.Column(
            "summary",
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
            "completed_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_pool_pipeline_runs_user_id"),
        "pool_pipeline_runs",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "pool_saved_searches",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("zipcode", sa.String(length=10), nullable=False),
        sa.Column(
            "radius_mi",
            sa.Float(),
            nullable=False,
            server_default=sa.text("5.0"),
        ),
        sa.Column("max_budget", sa.Integer(), nullable=True),
        sa.Column("min_budget", sa.Integer(), nullable=True),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_pool_saved_searches_user_id"),
        "pool_saved_searches",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_pool_saved_searches_user_id"),
        table_name="pool_saved_searches",
    )
    op.drop_table("pool_saved_searches")

    op.drop_index(
        op.f("ix_pool_pipeline_runs_user_id"),
        table_name="pool_pipeline_runs",
    )
    op.drop_table("pool_pipeline_runs")

    _RUN_STATUS_ENUM.drop(op.get_bind(), checkfirst=True)
