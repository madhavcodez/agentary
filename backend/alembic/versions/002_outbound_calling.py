"""Add contacts, call_campaigns, call_logs tables for outbound calling

Revision ID: 002
Revises: 001
Create Date: 2026-03-19
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("source", sa.String(100), server_default="manual"),
        sa.Column(
            "opportunity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("opportunities.id"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_contacts_company", "contacts", ["company"])
    op.create_index("ix_contacts_phone", "contacts", ["phone"])

    op.create_table(
        "call_campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "match_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("matches.id"),
            nullable=False,
        ),
        sa.Column(
            "contact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contacts.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("scheduled_at", sa.DateTime, nullable=True),
        sa.Column("priority", sa.Integer, server_default="0"),
        sa.Column("script_json", postgresql.JSON, nullable=True),
        sa.Column("max_attempts", sa.Integer, server_default="3"),
        sa.Column("attempt_count", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_call_campaigns_status", "call_campaigns", ["status"])
    op.create_index("ix_call_campaigns_scheduled_at", "call_campaigns", ["scheduled_at"])

    op.create_table(
        "call_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "campaign_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("call_campaigns.id"),
            nullable=False,
        ),
        sa.Column("twilio_call_sid", sa.String(100), nullable=True),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("ended_at", sa.DateTime, nullable=True),
        sa.Column("duration_sec", sa.Integer, nullable=True),
        sa.Column("outcome", sa.String(50), nullable=True),
        sa.Column("person_reached", sa.String(50), nullable=True),
        sa.Column("transcript", sa.Text, nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("recording_url", sa.String(1000), nullable=True),
        sa.Column("next_steps", postgresql.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_call_logs_campaign_id", "call_logs", ["campaign_id"])
    op.create_index("ix_call_logs_twilio_call_sid", "call_logs", ["twilio_call_sid"])


def downgrade() -> None:
    op.drop_index("ix_call_logs_twilio_call_sid")
    op.drop_index("ix_call_logs_campaign_id")
    op.drop_table("call_logs")
    op.drop_index("ix_call_campaigns_scheduled_at")
    op.drop_index("ix_call_campaigns_status")
    op.drop_table("call_campaigns")
    op.drop_index("ix_contacts_phone")
    op.drop_index("ix_contacts_company")
    op.drop_table("contacts")
