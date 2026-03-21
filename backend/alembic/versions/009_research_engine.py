"""research engine: projects, expert_agents, missions, crews, runs, tasks, findings, mission_research_results

Revision ID: 009
Revises: 008
Create Date: 2026-03-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Projects ──────────────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # ── Expert Agents ─────────────────────────────────────────────────
    op.create_table(
        "expert_agents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("avatar_emoji", sa.String(10), nullable=False, server_default="🤖"),
        sa.Column("category", sa.String(50), nullable=False, server_default="research"),
        sa.Column("capabilities", ARRAY(sa.String), server_default="{}"),
        sa.Column("tools", ARRAY(sa.String), server_default="{}"),
        sa.Column("system_prompt", sa.Text, nullable=False),
        sa.Column("model", sa.String(100), nullable=False, server_default="gemini-2.5-flash"),
        sa.Column("temperature", sa.Float, nullable=False, server_default="0.3"),
        sa.Column("max_tokens", sa.Integer, nullable=False, server_default="8192"),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # ── Missions ──────────────────────────────────────────────────────
    op.create_table(
        "missions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False, index=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("objective", sa.Text, nullable=True),
        sa.Column("scope", JSONB, server_default="{}"),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("required_experts", ARRAY(sa.String), nullable=True),
        sa.Column("max_experts", sa.Integer, nullable=False, server_default="5"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="normal"),
        sa.Column("schedule_cron", sa.String(100), nullable=True),
        sa.Column("is_recurring", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("confidence_score", sa.Float, nullable=True),
        sa.Column("findings_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
    )

    # ── Agent Crews ───────────────────────────────────────────────────
    op.create_table(
        "agent_crews",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("mission_id", UUID(as_uuid=True), sa.ForeignKey("missions.id"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("expert_agent_ids", ARRAY(UUID(as_uuid=True)), server_default="{}"),
        sa.Column("lead_agent_id", UUID(as_uuid=True), sa.ForeignKey("expert_agents.id"), nullable=True),
        sa.Column("collaboration_mode", sa.String(50), nullable=False, server_default="parallel"),
        sa.Column("max_iterations", sa.Integer, nullable=False, server_default="3"),
        sa.Column("time_limit_seconds", sa.Integer, nullable=False, server_default="3600"),
        sa.Column("status", sa.String(50), nullable=False, server_default="assembled"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # ── Crew Runs ─────────────────────────────────────────────────────
    op.create_table(
        "crew_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("crew_id", UUID(as_uuid=True), sa.ForeignKey("agent_crews.id"), nullable=False, index=True),
        sa.Column("mission_id", UUID(as_uuid=True), sa.ForeignKey("missions.id"), nullable=False, index=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="queued"),
        sa.Column("trigger_type", sa.String(50), nullable=False, server_default="manual"),
        sa.Column("iteration", sa.Integer, nullable=False, server_default="1"),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("metrics", JSONB, server_default="{}"),
        sa.Column("error", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # ── Crew Tasks ────────────────────────────────────────────────────
    op.create_table(
        "crew_tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("crew_runs.id"), nullable=False, index=True),
        sa.Column("expert_agent_id", UUID(as_uuid=True), sa.ForeignKey("expert_agents.id"), nullable=False, index=True),
        sa.Column("task_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("input_data", JSONB, server_default="{}"),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("thinking_log", JSONB, server_default="[]"),
        sa.Column("output_data", JSONB, nullable=True),
        sa.Column("findings_produced", sa.Integer, nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("tokens_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # ── Findings ──────────────────────────────────────────────────────
    op.create_table(
        "findings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("mission_id", UUID(as_uuid=True), sa.ForeignKey("missions.id"), nullable=False, index=True),
        sa.Column("crew_task_id", UUID(as_uuid=True), sa.ForeignKey("crew_tasks.id"), nullable=True, index=True),
        sa.Column("expert_agent_id", UUID(as_uuid=True), sa.ForeignKey("expert_agents.id"), nullable=True),
        sa.Column("category", sa.String(50), nullable=False, server_default="data_point"),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("structured_data", JSONB, nullable=True),
        sa.Column("source_type", sa.String(50), nullable=True),
        sa.Column("source_url", sa.Text, nullable=True),
        sa.Column("source_name", sa.String(255), nullable=True),
        sa.Column("source_raw", sa.Text, nullable=True),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("verified", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("verification_sources", JSONB, nullable=True),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("tags", ARRAY(sa.String), server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # ── Mission Research Results ──────────────────────────────────────
    op.create_table(
        "mission_research_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("mission_id", UUID(as_uuid=True), sa.ForeignKey("missions.id"), nullable=False, index=True),
        sa.Column("crew_run_id", UUID(as_uuid=True), sa.ForeignKey("crew_runs.id"), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("sections", JSONB, server_default="[]"),
        sa.Column("structured_data", JSONB, nullable=True),
        sa.Column("raw_data", JSONB, nullable=True),
        sa.Column("sources_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column("findings_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("methodology", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("mission_research_results")
    op.drop_table("findings")
    op.drop_table("crew_tasks")
    op.drop_table("crew_runs")
    op.drop_table("agent_crews")
    op.drop_table("missions")
    op.drop_table("expert_agents")
    op.drop_table("projects")
