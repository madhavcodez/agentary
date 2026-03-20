"""Add email events, suppressions, and resend_email_id to campaigns

Revision ID: 006
Revises: 005
Create Date: 2026-03-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # email_events table (with user_id for multi-tenancy)
    op.create_table(
        "email_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "campaign_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("call_campaigns.id"),
            nullable=True,
        ),
        sa.Column("resend_email_id", sa.String(100), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("payload", postgresql.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_email_events_user_id", "email_events", ["user_id"])
    op.create_index("ix_email_events_campaign_id", "email_events", ["campaign_id"])
    op.create_index("ix_email_events_resend_email_id", "email_events", ["resend_email_id"])
    op.create_index("ix_email_events_event_type", "email_events", ["event_type"])

    # email_suppressions table (global, not user-scoped)
    op.create_table(
        "email_suppressions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), unique=True, nullable=False),
        sa.Column("reason", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_email_suppressions_email", "email_suppressions", ["email"])

    # Add resend_email_id to call_campaigns for linking sends to events
    op.add_column(
        "call_campaigns",
        sa.Column("resend_email_id", sa.String(100), nullable=True),
    )
    op.create_index(
        "ix_call_campaigns_resend_email_id", "call_campaigns", ["resend_email_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_call_campaigns_resend_email_id", table_name="call_campaigns")
    op.drop_column("call_campaigns", "resend_email_id")

    op.drop_index("ix_email_suppressions_email", table_name="email_suppressions")
    op.drop_table("email_suppressions")

    op.drop_index("ix_email_events_event_type", table_name="email_events")
    op.drop_index("ix_email_events_resend_email_id", table_name="email_events")
    op.drop_index("ix_email_events_campaign_id", table_name="email_events")
    op.drop_index("ix_email_events_user_id", table_name="email_events")
    op.drop_table("email_events")
