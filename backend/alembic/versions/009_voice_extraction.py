"""Add voice extraction tables: voice_sessions, extraction_templates, findings

Revision ID: 009
Revises: 008
Create Date: 2026-03-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, JSONB, UUID, ARRAY

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- voice_sessions --
    op.create_table(
        "voice_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("mission_id", UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("crew_task_id", UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("batch_id", UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("template_id", UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("session_type", sa.String(50), nullable=False, server_default="research_extraction"),
        sa.Column("status", sa.String(50), nullable=False, server_default="planned"),
        sa.Column("target_name", sa.String(500), nullable=False),
        sa.Column("target_phone", sa.String(50), nullable=False),
        sa.Column("target_business", sa.String(500), nullable=True),
        sa.Column("target_context", JSON, nullable=True),
        sa.Column("persona_config", JSON, nullable=True),
        sa.Column("extraction_goals", JSON, nullable=True),
        sa.Column("call_script", sa.Text, nullable=True),
        sa.Column("system_prompt", sa.Text, nullable=True),
        sa.Column("twilio_call_sid", sa.String(100), nullable=True),
        sa.Column("recording_url", sa.Text, nullable=True),
        sa.Column("transcript", sa.Text, nullable=True),
        sa.Column("transcript_segments", JSON, nullable=True),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("outcome", sa.String(50), nullable=True),
        sa.Column("extracted_data", JSON, nullable=True),
        sa.Column("extraction_confidence", sa.Float, nullable=True),
        sa.Column("cost_usd", sa.Float, nullable=True),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("connected_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # -- extraction_templates --
    op.create_table(
        "extraction_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("category", sa.String(50), nullable=False, server_default="custom"),
        sa.Column("extraction_fields", JSON, nullable=False),
        sa.Column("persona_template", JSON, nullable=True),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # -- findings --
    op.create_table(
        "findings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("mission_id", UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("crew_task_id", UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("expert_agent_id", UUID(as_uuid=True), nullable=True),
        sa.Column("voice_session_id", UUID(as_uuid=True), sa.ForeignKey("voice_sessions.id"), nullable=True, index=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("category", sa.String(50), nullable=False, server_default="data_point"),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("structured_data", JSONB, nullable=True),
        sa.Column("source_type", sa.String(50), nullable=True),
        sa.Column("source_url", sa.Text, nullable=True),
        sa.Column("source_name", sa.String(255), nullable=True),
        sa.Column("source_raw", sa.Text, nullable=True),
        sa.Column("confidence", sa.Float, nullable=False, server_default=sa.text("0.5")),
        sa.Column("verified", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("verification_sources", JSONB, nullable=True),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("tags", ARRAY(sa.String), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("findings")
    op.drop_table("extraction_templates")
    op.drop_table("voice_sessions")
