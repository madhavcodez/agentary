"""Add research_results table and outreach columns to call_campaigns

Revision ID: 003
Revises: 002
Create Date: 2026-03-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- New table: research_results ---
    op.create_table(
        "research_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "match_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("matches.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("company_intel", postgresql.JSON, nullable=True),
        sa.Column("contacts_found", postgresql.JSON, nullable=True),
        sa.Column("sources_used", postgresql.JSON, nullable=True),
        sa.Column("quality_score", sa.Float, server_default="0.0"),
        sa.Column("researched_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_research_results_match_id",
        "research_results",
        ["match_id"],
        unique=True,
    )

    # --- New columns on call_campaigns for multi-channel outreach ---
    op.add_column(
        "call_campaigns",
        sa.Column("email_subject", sa.String(500), nullable=True),
    )
    op.add_column(
        "call_campaigns",
        sa.Column("email_draft", sa.Text, nullable=True),
    )
    op.add_column(
        "call_campaigns",
        sa.Column("email_sent_at", sa.DateTime, nullable=True),
    )
    op.add_column(
        "call_campaigns",
        sa.Column("linkedin_msg", sa.Text, nullable=True),
    )
    op.add_column(
        "call_campaigns",
        sa.Column("linkedin_sent_at", sa.DateTime, nullable=True),
    )
    op.add_column(
        "call_campaigns",
        sa.Column("outreach_sequence", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("call_campaigns", "outreach_sequence")
    op.drop_column("call_campaigns", "linkedin_sent_at")
    op.drop_column("call_campaigns", "linkedin_msg")
    op.drop_column("call_campaigns", "email_sent_at")
    op.drop_column("call_campaigns", "email_draft")
    op.drop_column("call_campaigns", "email_subject")
    op.drop_index("ix_research_results_match_id")
    op.drop_table("research_results")
