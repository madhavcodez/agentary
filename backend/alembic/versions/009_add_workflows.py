"""Add workflow engine tables

Revision ID: 009
Revises: 008
Create Date: 2026-03-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # WorkflowTemplate first (referenced by Workflow)
    op.create_table(
        "workflow_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("category", sa.String(30), nullable=False, server_default="custom"),
        sa.Column("tags", ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("nodes_template", JSONB, nullable=False, server_default="[]"),
        sa.Column("edges_template", JSONB, nullable=False, server_default="[]"),
        sa.Column("variables_schema", JSONB, nullable=False, server_default="[]"),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_public", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("install_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "workflows",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("trigger_type", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("trigger_config", JSONB, nullable=True),
        sa.Column("created_from", sa.String(30), nullable=False, server_default="visual_editor"),
        sa.Column("template_id", UUID(as_uuid=True), sa.ForeignKey("workflow_templates.id"), nullable=True),
        sa.Column("nodes", JSONB, nullable=False, server_default="[]"),
        sa.Column("edges", JSONB, nullable=False, server_default="[]"),
        sa.Column("variables", JSONB, nullable=False, server_default="{}"),
        sa.Column("last_run_at", sa.DateTime, nullable=True),
        sa.Column("total_runs", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("avg_duration_seconds", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_workflows_status", "workflows", ["status"])

    op.create_table(
        "workflow_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workflow_id", UUID(as_uuid=True), sa.ForeignKey("workflows.id"), nullable=False, index=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("trigger_type", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("node_results", JSONB, nullable=False, server_default="{}"),
        sa.Column("output_data", JSONB, nullable=True),
        sa.Column("findings_generated", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("error", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("workflow_runs")
    op.drop_index("ix_workflows_status", table_name="workflows")
    op.drop_table("workflows")
    op.drop_table("workflow_templates")
