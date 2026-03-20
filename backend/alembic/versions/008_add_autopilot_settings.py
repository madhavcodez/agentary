"""Add users table with autopilot scheduling preferences

Revision ID: 008
Revises: 003
Create Date: 2026-03-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "008"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("profiles.id"),
            nullable=True,
            unique=True,
        ),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column(
            "autopilot_enabled",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("autopilot_cron", sa.String(100), nullable=True),
        sa.Column(
            "autopilot_timezone",
            sa.String(50),
            nullable=False,
            server_default="America/Los_Angeles",
        ),
        sa.Column(
            "autopilot_business_hours_only",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_profile_id", "users", ["profile_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_profile_id")
    op.drop_index("ix_users_email")
    op.drop_table("users")
