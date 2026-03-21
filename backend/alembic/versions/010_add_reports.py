"""Add reports table for report generation and export

Revision ID: 010
Revises: 009
Create Date: 2026-03-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

revision = "010"
down_revision = "009b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("mission_id", UUID(as_uuid=True), sa.ForeignKey("missions.id"), nullable=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("report_type", sa.String(50), nullable=False, server_default="research_report"),
        sa.Column("status", sa.String(20), nullable=False, server_default="generating"),
        sa.Column("content_markdown", sa.Text, nullable=True),
        sa.Column("content_html", sa.Text, nullable=True),
        sa.Column("sections", JSON, nullable=True),
        sa.Column("executive_summary", sa.Text, nullable=True),
        sa.Column("methodology", sa.Text, nullable=True),
        sa.Column("sources", JSON, nullable=True),
        sa.Column("charts", JSON, nullable=True),
        sa.Column("structured_data", JSON, nullable=True),
        sa.Column("metadata", JSON, nullable=True),
        sa.Column("format_config", JSON, nullable=True),
        sa.Column("share_token", sa.String(255), nullable=True, unique=True),
        sa.Column("share_enabled", sa.Boolean, server_default="false"),
        sa.Column("pdf_url", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_reports_user_id", "reports", ["user_id"])
    op.create_index("ix_reports_project_id", "reports", ["project_id"])
    op.create_index("ix_reports_mission_id", "reports", ["mission_id"])
    op.create_index("ix_reports_share_token", "reports", ["share_token"])


def downgrade() -> None:
    op.drop_index("ix_reports_share_token")
    op.drop_index("ix_reports_mission_id")
    op.drop_index("ix_reports_project_id")
    op.drop_index("ix_reports_user_id")
    op.drop_table("reports")
