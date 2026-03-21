"""Add data_sources, source_request_logs, entities, entity_collections tables

Revision ID: 011
Revises: 010b
Create Date: 2026-03-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID

revision = "011"
down_revision = "010b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_sources",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("config", JSON, server_default="{}"),
        sa.Column("auth_config", JSON, server_default="{}"),
        sa.Column("rate_limit", JSON, server_default="{}"),
        sa.Column("cost_per_request", sa.Float, nullable=True),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("health_status", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("last_health_check", sa.DateTime, nullable=True),
        sa.Column("total_requests", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_cost_usd", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "source_request_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("data_source_id", UUID(as_uuid=True), sa.ForeignKey("data_sources.id"), nullable=False),
        sa.Column("mission_id", UUID(as_uuid=True), nullable=True),
        sa.Column("crew_task_id", UUID(as_uuid=True), nullable=True),
        sa.Column("request_type", sa.String(50), nullable=False),
        sa.Column("request_params", JSON, server_default="{}"),
        sa.Column("response_status", sa.Integer, nullable=True),
        sa.Column("response_preview", sa.Text, nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("cost_usd", sa.Float, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_source_request_logs_source_created",
        "source_request_logs",
        ["data_source_id", "created_at"],
    )

    op.create_table(
        "entities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("canonical_data", JSON, server_default="{}"),
        sa.Column("aliases", ARRAY(sa.String), server_default="{}"),
        sa.Column("source_urls", ARRAY(sa.String), server_default="{}"),
        sa.Column("tags", ARRAY(sa.String), server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_entities_type_name", "entities", ["entity_type", "name"])

    op.create_table(
        "entity_collections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_ids", ARRAY(UUID(as_uuid=True)), server_default="{}"),
        sa.Column("filters", JSON, nullable=True),
        sa.Column("count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("entity_collections")
    op.drop_index("ix_entities_type_name", table_name="entities")
    op.drop_table("entities")
    op.drop_index("ix_source_request_logs_source_created", table_name="source_request_logs")
    op.drop_table("source_request_logs")
    op.drop_table("data_sources")
