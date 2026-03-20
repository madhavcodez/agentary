"""Add autopilot scheduling columns to users table

Revision ID: 008
Revises: 007
Create Date: 2026-03-19
"""

from alembic import op
import sqlalchemy as sa

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("autopilot_enabled", sa.Boolean, nullable=False, server_default=sa.text("false")))
    op.add_column("users", sa.Column("autopilot_cron", sa.String(100), nullable=True))
    op.add_column("users", sa.Column("autopilot_timezone", sa.String(50), nullable=False, server_default="America/Los_Angeles"))
    op.add_column("users", sa.Column("autopilot_business_hours_only", sa.Boolean, nullable=False, server_default=sa.text("true")))


def downgrade() -> None:
    op.drop_column("users", "autopilot_business_hours_only")
    op.drop_column("users", "autopilot_timezone")
    op.drop_column("users", "autopilot_cron")
    op.drop_column("users", "autopilot_enabled")
