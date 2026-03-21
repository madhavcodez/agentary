"""Agentary restructure: archive old domain tables, create new agent-based schema

Rename old job-search tables with _archived_ prefix and create all new tables
for the Agentary research/intelligence platform: projects, missions, expert_agents,
agent_crews, agent_activities, mission_runs, mission_tasks, findings, datasets,
data_rows, reports, voice_extractions, call_records, workflows, workflow_templates,
workflow_runs, monitors, alerts, knowledge_bases, sources, audit_logs.

Revision ID: 009
Revises: 008
Create Date: 2026-03-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, JSON, UUID

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None

# ── Old tables to archive (rename with _archived_ prefix) ──────────────────
ARCHIVE_TABLES = [
    "pipeline_transitions",
    "email_events",
    "email_suppressions",
    "call_campaigns",
    "dossiers",
    "matches",
    "opportunities",
    "preferences",
    "experiences",
    "skills",
    "profiles",
]

# Indexes to drop before renaming (table_name -> list of index names)
ARCHIVE_INDEXES = {
    "opportunities": ["ix_opportunities_source"],
    "call_campaigns": [
        "ix_call_campaigns_status",
        "ix_call_campaigns_scheduled_at",
        "ix_call_campaigns_resend_email_id",
    ],
    "email_events": [
        "ix_email_events_user_id",
        "ix_email_events_campaign_id",
        "ix_email_events_resend_email_id",
        "ix_email_events_event_type",
    ],
    "email_suppressions": ["ix_email_suppressions_email"],
    "pipeline_transitions": [],
    "matches": ["ix_matches_pipeline_stage"],
}


def upgrade() -> None:
    # ──────────────────────────────────────────────────────────────────────
    # PHASE 1: Archive old tables
    # ──────────────────────────────────────────────────────────────────────
    for table in ARCHIVE_TABLES:
        # Drop known indexes first (some reference table name)
        for idx in ARCHIVE_INDEXES.get(table, []):
            op.execute(sa.text(f"DROP INDEX IF EXISTS {idx}"))

        op.execute(
            sa.text(
                f"ALTER TABLE IF EXISTS {table} RENAME TO _archived_{table}"
            )
        )

    # ──────────────────────────────────────────────────────────────────────
    # PHASE 2: Create enum types
    # ──────────────────────────────────────────────────────────────────────
    op.execute("CREATE TYPE projectstatus AS ENUM ('active', 'archived', 'completed')")
    op.execute(
        "CREATE TYPE projecttype AS ENUM ("
        "'market_research', 'competitive_intel', 'due_diligence', "
        "'data_extraction', 'real_estate', 'local_business', 'custom')"
    )
    op.execute(
        "CREATE TYPE missionstatus AS ENUM ("
        "'draft', 'queued', 'running', 'paused', 'completed', 'failed')"
    )
    op.execute(
        "CREATE TYPE missiontype AS ENUM ("
        "'research', 'voice_extraction', 'monitoring', "
        "'data_collection', 'competitive_analysis', 'custom')"
    )
    op.execute(
        "CREATE TYPE agentspecialty AS ENUM ("
        "'web_researcher', 'data_extractor', 'voice_caller', "
        "'market_analyst', 'financial_analyst', 'real_estate_expert', "
        "'competitive_intel', 'due_diligence', 'synthesizer', 'local_business_intel')"
    )
    op.execute(
        "CREATE TYPE coordinationstrategy AS ENUM ("
        "'parallel', 'sequential', 'hierarchical')"
    )
    op.execute(
        "CREATE TYPE activitytype AS ENUM ("
        "'thinking', 'searching', 'scraping', 'calling', 'analyzing', "
        "'writing', 'found_data', 'found_insight', 'error', 'delegating', 'synthesizing')"
    )
    op.execute(
        "CREATE TYPE runstatus AS ENUM ("
        "'queued', 'running', 'completed', 'failed', 'cancelled')"
    )
    op.execute(
        "CREATE TYPE triggertype AS ENUM ('manual', 'scheduled', 'monitor_triggered')"
    )
    op.execute(
        "CREATE TYPE tasktype AS ENUM ("
        "'discover', 'research', 'extract', 'call', 'analyze', "
        "'synthesize', 'report', 'monitor_check')"
    )
    op.execute(
        "CREATE TYPE taskstatus AS ENUM ("
        "'pending', 'running', 'completed', 'failed', 'skipped')"
    )
    op.execute(
        "CREATE TYPE findingtype AS ENUM ("
        "'fact', 'data_point', 'insight', 'quote', 'statistic', "
        "'contact_info', 'price', 'availability', 'sentiment', "
        "'trend', 'anomaly', 'opportunity', 'risk')"
    )
    op.execute(
        "CREATE TYPE sourcetype AS ENUM ("
        "'web', 'voice_call', 'api', 'public_record', 'user_provided', 'inferred')"
    )
    op.execute(
        "CREATE TYPE voiceextractionstatus AS ENUM ("
        "'draft', 'active', 'paused', 'completed')"
    )
    op.execute("CREATE TYPE calldirection AS ENUM ('outbound', 'inbound')")
    op.execute(
        "CREATE TYPE callstatus AS ENUM ("
        "'pending', 'ringing', 'connected', 'completed', 'failed', 'no_answer', 'voicemail')"
    )
    op.execute(
        "CREATE TYPE monitorstatus AS ENUM ('active', 'paused', 'archived')"
    )
    op.execute(
        "CREATE TYPE monitortype AS ENUM ("
        "'web_content', 'api_data', 'price_tracker', "
        "'listing_watcher', 'competitor_tracker', 'custom')"
    )
    op.execute("CREATE TYPE alertseverity AS ENUM ('info', 'warning', 'critical')")
    op.execute(
        "CREATE TYPE kbdomain AS ENUM ("
        "'real_estate', 'finance', 'technology', "
        "'healthcare', 'retail', 'custom')"
    )
    op.execute(
        "CREATE TYPE sourcekind AS ENUM ("
        "'web_search', 'web_scrape', 'api', 'public_records', 'mls', "
        "'county_records', 'voice', 'rss', 'social_media', 'file_upload', 'database')"
    )
    op.execute(
        "CREATE TYPE auditaction AS ENUM ("
        "'created', 'updated', 'deleted', 'executed', 'accessed')"
    )

    # ──────────────────────────────────────────────────────────────────────
    # PHASE 3: Create new tables
    # ──────────────────────────────────────────────────────────────────────

    # -- knowledge_bases (referenced by projects.knowledge_base_id) --------
    op.create_table(
        "knowledge_bases",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("domain", sa.Enum("real_estate", "finance", "technology", "healthcare", "retail", "custom", name="kbdomain", create_type=False), nullable=True),
        sa.Column("context_text", sa.Text, nullable=True),
        sa.Column("entities", JSONB, server_default="[]"),
        sa.Column("terminology", JSONB, server_default="{}"),
        sa.Column("preferences", JSONB, server_default="{}"),
        sa.Column("documents", JSONB, server_default="[]"),
        sa.Column("qdrant_collection", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- sources -----------------------------------------------------------
    op.create_table(
        "sources",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_type", sa.Enum("web_search", "web_scrape", "api", "public_records", "mls", "county_records", "voice", "rss", "social_media", "file_upload", "database", name="sourcekind", create_type=False), nullable=False),
        sa.Column("adapter_slug", sa.String(100), nullable=True),
        sa.Column("config", JSONB, server_default="{}"),
        sa.Column("credentials_ref", JSONB, server_default="{}"),
        sa.Column("rate_limit", JSONB, server_default="{}"),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("is_system", sa.Boolean, server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- workflow_templates (referenced by workflows.template_id) ----------
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
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # -- workflows ---------------------------------------------------------
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
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_runs", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("avg_duration_seconds", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_workflows_status", "workflows", ["status"])

    # -- projects ----------------------------------------------------------
    op.create_table(
        "projects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.Enum("active", "archived", "completed", name="projectstatus", create_type=False), nullable=False, server_default="active"),
        sa.Column("project_type", sa.Enum("market_research", "competitive_intel", "due_diligence", "data_extraction", "real_estate", "local_business", "custom", name="projecttype", create_type=False), nullable=False, server_default="custom"),
        sa.Column("domain_context", sa.Text, nullable=True),
        sa.Column("knowledge_base_id", UUID(as_uuid=True), sa.ForeignKey("knowledge_bases.id"), nullable=True),
        sa.Column("default_workflow_id", UUID(as_uuid=True), sa.ForeignKey("workflows.id"), nullable=True),
        sa.Column("total_missions", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("total_findings", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("total_calls_made", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("total_reports_generated", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Add deferred FK from workflows.project_id -> projects.id
    op.create_foreign_key(
        "fk_workflows_project_id",
        "workflows",
        "projects",
        ["project_id"],
        ["id"],
    )

    # -- expert_agents -----------------------------------------------------
    op.create_table(
        "expert_agents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("specialty", sa.Enum("web_researcher", "data_extractor", "voice_caller", "market_analyst", "financial_analyst", "real_estate_expert", "competitive_intel", "due_diligence", "synthesizer", "local_business_intel", name="agentspecialty", create_type=False), nullable=False),
        sa.Column("system_prompt", sa.Text, nullable=True),
        sa.Column("tools", JSONB, server_default="[]"),
        sa.Column("model_config", JSONB, server_default="{}"),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("color", sa.String(7), nullable=True),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- missions ----------------------------------------------------------
    op.create_table(
        "missions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False, index=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("objective", sa.Text, nullable=True),
        sa.Column("status", sa.Enum("draft", "queued", "running", "paused", "completed", "failed", name="missionstatus", create_type=False), nullable=False, server_default="draft"),
        sa.Column("mission_type", sa.Enum("research", "voice_extraction", "monitoring", "data_collection", "competitive_analysis", "custom", name="missiontype", create_type=False), nullable=False, server_default="research"),
        sa.Column("instructions", sa.Text, nullable=True),
        sa.Column("parameters", JSONB, server_default="{}"),
        sa.Column("workflow_id", UUID(as_uuid=True), sa.ForeignKey("workflows.id"), nullable=True),
        sa.Column("crew_config", JSONB, server_default="{}"),
        sa.Column("schedule_cron", sa.String(100), nullable=True),
        sa.Column("timezone", sa.String(50), server_default="UTC"),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("findings_count", sa.Integer, server_default=sa.text("0")),
        sa.Column("confidence_score", sa.Float, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- agent_crews -------------------------------------------------------
    op.create_table(
        "agent_crews",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("mission_id", UUID(as_uuid=True), sa.ForeignKey("missions.id"), nullable=False, index=True),
        sa.Column("agents", JSONB, server_default="[]"),
        sa.Column("coordination_strategy", sa.Enum("parallel", "sequential", "hierarchical", name="coordinationstrategy", create_type=False), server_default="parallel"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- mission_runs ------------------------------------------------------
    op.create_table(
        "mission_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("mission_id", UUID(as_uuid=True), sa.ForeignKey("missions.id"), nullable=False, index=True),
        sa.Column("status", sa.Enum("queued", "running", "completed", "failed", "cancelled", name="runstatus", create_type=False), nullable=False, server_default="queued"),
        sa.Column("trigger_type", sa.Enum("manual", "scheduled", "monitor_triggered", name="triggertype", create_type=False), nullable=False, server_default="manual"),
        sa.Column("config_snapshot", JSONB, server_default="{}"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("metrics", JSONB, server_default="{}"),
        sa.Column("error", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- crew_runs (referenced by agent_activities.run_id) -----------------
    op.create_table(
        "crew_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("crew_id", UUID(as_uuid=True), sa.ForeignKey("agent_crews.id"), nullable=False, index=True),
        sa.Column("mission_id", UUID(as_uuid=True), sa.ForeignKey("missions.id"), nullable=False, index=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="queued"),
        sa.Column("trigger_type", sa.String(50), nullable=False, server_default="manual"),
        sa.Column("iteration", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("metrics", JSONB, server_default="{}"),
        sa.Column("error", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- agent_activities --------------------------------------------------
    op.create_table(
        "agent_activities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("mission_id", UUID(as_uuid=True), sa.ForeignKey("missions.id"), nullable=False, index=True),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("crew_runs.id"), nullable=True, index=True),
        sa.Column("crew_id", UUID(as_uuid=True), sa.ForeignKey("agent_crews.id"), nullable=True, index=True),
        sa.Column("expert_agent_id", UUID(as_uuid=True), sa.ForeignKey("expert_agents.id"), nullable=True),
        sa.Column("activity_type", sa.Enum("thinking", "searching", "scraping", "calling", "analyzing", "writing", "found_data", "found_insight", "error", "delegating", "synthesizing", name="activitytype", create_type=False), nullable=False),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("metadata", JSONB, server_default="{}"),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- mission_tasks -----------------------------------------------------
    op.create_table(
        "mission_tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("mission_runs.id"), nullable=False, index=True),
        sa.Column("expert_agent_id", UUID(as_uuid=True), sa.ForeignKey("expert_agents.id"), nullable=True),
        sa.Column("task_type", sa.Enum("discover", "research", "extract", "call", "analyze", "synthesize", "report", "monitor_check", name="tasktype", create_type=False), nullable=False),
        sa.Column("status", sa.Enum("pending", "running", "completed", "failed", "skipped", name="taskstatus", create_type=False), nullable=False, server_default="pending"),
        sa.Column("input_data", JSONB, server_default="{}"),
        sa.Column("result_data", JSONB, server_default="{}"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("retry_count", sa.Integer, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- voice_extractions -------------------------------------------------
    op.create_table(
        "voice_extractions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False, index=True),
        sa.Column("mission_id", UUID(as_uuid=True), sa.ForeignKey("missions.id"), nullable=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.Enum("draft", "active", "paused", "completed", name="voiceextractionstatus", create_type=False), nullable=False, server_default="draft"),
        sa.Column("objective", sa.Text, nullable=True),
        sa.Column("persona", JSONB, server_default="{}"),
        sa.Column("extraction_schema", JSONB, server_default="{}"),
        sa.Column("call_script_template", sa.Text, nullable=True),
        sa.Column("objection_handlers", JSONB, server_default="[]"),
        sa.Column("max_call_duration_seconds", sa.Integer, server_default=sa.text("300")),
        sa.Column("business_hours_only", sa.Boolean, server_default=sa.text("true")),
        sa.Column("targets", JSONB, server_default="[]"),
        sa.Column("total_targets", sa.Integer, server_default=sa.text("0")),
        sa.Column("calls_completed", sa.Integer, server_default=sa.text("0")),
        sa.Column("calls_successful", sa.Integer, server_default=sa.text("0")),
        sa.Column("data_points_extracted", sa.Integer, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- call_records ------------------------------------------------------
    op.create_table(
        "call_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("voice_extraction_id", UUID(as_uuid=True), sa.ForeignKey("voice_extractions.id"), nullable=False, index=True),
        sa.Column("mission_id", UUID(as_uuid=True), sa.ForeignKey("missions.id"), nullable=True, index=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=True, index=True),
        sa.Column("phone_number", sa.String(20), nullable=True),
        sa.Column("target_name", sa.String(255), nullable=True),
        sa.Column("target_context", JSONB, server_default="{}"),
        sa.Column("provider_call_id", sa.String(255), nullable=True),
        sa.Column("direction", sa.Enum("outbound", "inbound", name="calldirection", create_type=False), server_default="outbound"),
        sa.Column("status", sa.Enum("pending", "ringing", "connected", "completed", "failed", "no_answer", "voicemail", name="callstatus", create_type=False), nullable=False, server_default="pending"),
        sa.Column("recording_url", sa.String(2048), nullable=True),
        sa.Column("transcript", sa.Text, nullable=True),
        sa.Column("duration_seconds", sa.Integer, nullable=True),
        sa.Column("extracted_data", JSONB, server_default="{}"),
        sa.Column("extraction_confidence", sa.Float, nullable=True),
        sa.Column("extraction_notes", sa.Text, nullable=True),
        sa.Column("sentiment", sa.String(20), nullable=True),
        sa.Column("call_quality_score", sa.Float, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- findings ----------------------------------------------------------
    op.create_table(
        "findings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False, index=True),
        sa.Column("mission_id", UUID(as_uuid=True), sa.ForeignKey("missions.id"), nullable=True, index=True),
        sa.Column("expert_agent_id", UUID(as_uuid=True), sa.ForeignKey("expert_agents.id"), nullable=True),
        sa.Column("call_record_id", UUID(as_uuid=True), sa.ForeignKey("call_records.id"), nullable=True, index=True),
        sa.Column("finding_type", sa.Enum("fact", "data_point", "insight", "quote", "statistic", "contact_info", "price", "availability", "sentiment", "trend", "anomaly", "opportunity", "risk", name="findingtype", create_type=False), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("structured_data", JSONB, server_default="{}"),
        sa.Column("source_type", sa.Enum("web", "voice_call", "api", "public_record", "user_provided", "inferred", name="sourcetype", create_type=False), nullable=True),
        sa.Column("source_url", sa.String(2048), nullable=True),
        sa.Column("source_name", sa.String(255), nullable=True),
        sa.Column("source_metadata", JSONB, server_default="{}"),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("verified", sa.Boolean, server_default=sa.text("false")),
        sa.Column("verified_by", UUID(as_uuid=True), nullable=True),
        sa.Column("contradicts", UUID(as_uuid=True), sa.ForeignKey("findings.id"), nullable=True),
        sa.Column("tags", JSONB, server_default="[]"),
        sa.Column("entity_refs", JSONB, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- datasets ----------------------------------------------------------
    op.create_table(
        "datasets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False, index=True),
        sa.Column("mission_id", UUID(as_uuid=True), sa.ForeignKey("missions.id"), nullable=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("schema_definition", JSONB, server_default="{}"),
        sa.Column("row_count", sa.Integer, server_default=sa.text("0")),
        sa.Column("data", JSONB, nullable=True),
        sa.Column("file_path", sa.String(1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- data_rows ---------------------------------------------------------
    op.create_table(
        "data_rows",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("dataset_id", UUID(as_uuid=True), sa.ForeignKey("datasets.id"), nullable=False, index=True),
        sa.Column("data", JSONB, nullable=False),
        sa.Column("source_finding_id", UUID(as_uuid=True), sa.ForeignKey("findings.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- reports -----------------------------------------------------------
    op.create_table(
        "reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=True, index=True),
        sa.Column("mission_id", UUID(as_uuid=True), sa.ForeignKey("missions.id"), nullable=True, index=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
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
        sa.Column("share_enabled", sa.Boolean, server_default=sa.text("false")),
        sa.Column("pdf_url", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_reports_share_token", "reports", ["share_token"])

    # -- monitors ----------------------------------------------------------
    op.create_table(
        "monitors",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=True, index=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.Enum("active", "paused", "archived", name="monitorstatus", create_type=False), nullable=False, server_default="active"),
        sa.Column("monitor_type", sa.Enum("web_content", "api_data", "price_tracker", "listing_watcher", "competitor_tracker", "custom", name="monitortype", create_type=False), nullable=False),
        sa.Column("check_config", JSONB, server_default="{}"),
        sa.Column("alert_config", JSONB, server_default="{}"),
        sa.Column("schedule_cron", sa.String(100), nullable=True),
        sa.Column("timezone", sa.String(50), server_default="UTC"),
        sa.Column("last_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_change_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_snapshot", JSONB, nullable=True),
        sa.Column("total_checks", sa.Integer, server_default=sa.text("0")),
        sa.Column("total_alerts", sa.Integer, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- alerts ------------------------------------------------------------
    op.create_table(
        "alerts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("monitor_id", UUID(as_uuid=True), sa.ForeignKey("monitors.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=True, index=True),
        sa.Column("alert_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("message", sa.Text, nullable=True),
        sa.Column("severity", sa.Enum("info", "warning", "critical", name="alertseverity", create_type=False), nullable=False, server_default="info"),
        sa.Column("data", JSONB, server_default="{}"),
        sa.Column("acknowledged", sa.Boolean, server_default=sa.text("false"), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("delivered_channels", ARRAY(sa.String), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- audit_logs --------------------------------------------------------
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=True, index=True),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.Enum("created", "updated", "deleted", "executed", "accessed", name="auditaction", create_type=False), nullable=False),
        sa.Column("details", JSONB, server_default="{}"),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- workflow_runs -----------------------------------------------------
    op.create_table(
        "workflow_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workflow_id", UUID(as_uuid=True), sa.ForeignKey("workflows.id"), nullable=False, index=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("trigger_type", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("node_results", JSONB, nullable=False, server_default="{}"),
        sa.Column("output_data", JSONB, nullable=True),
        sa.Column("findings_generated", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("error", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    # ──────────────────────────────────────────────────────────────────────
    # PHASE 1: Drop all new tables (reverse creation order)
    # ──────────────────────────────────────────────────────────────────────
    op.drop_table("workflow_runs")
    op.drop_table("audit_logs")
    op.drop_table("alerts")
    op.drop_table("monitors")
    op.drop_index("ix_reports_share_token", table_name="reports")
    op.drop_table("reports")
    op.drop_table("data_rows")
    op.drop_table("datasets")
    op.drop_table("findings")
    op.drop_table("call_records")
    op.drop_table("voice_extractions")
    op.drop_table("mission_tasks")
    op.drop_table("agent_activities")
    op.drop_table("crew_runs")
    op.drop_table("mission_runs")
    op.drop_table("agent_crews")
    op.drop_table("missions")
    op.drop_table("expert_agents")
    op.drop_table("projects")
    op.drop_constraint("fk_workflows_project_id", "workflows", type_="foreignkey")
    op.drop_index("ix_workflows_status", table_name="workflows")
    op.drop_table("workflows")
    op.drop_table("workflow_templates")
    op.drop_table("sources")
    op.drop_table("knowledge_bases")

    # ──────────────────────────────────────────────────────────────────────
    # PHASE 2: Drop enum types
    # ──────────────────────────────────────────────────────────────────────
    op.execute("DROP TYPE IF EXISTS auditaction")
    op.execute("DROP TYPE IF EXISTS sourcekind")
    op.execute("DROP TYPE IF EXISTS kbdomain")
    op.execute("DROP TYPE IF EXISTS alertseverity")
    op.execute("DROP TYPE IF EXISTS monitortype")
    op.execute("DROP TYPE IF EXISTS monitorstatus")
    op.execute("DROP TYPE IF EXISTS callstatus")
    op.execute("DROP TYPE IF EXISTS calldirection")
    op.execute("DROP TYPE IF EXISTS voiceextractionstatus")
    op.execute("DROP TYPE IF EXISTS sourcetype")
    op.execute("DROP TYPE IF EXISTS findingtype")
    op.execute("DROP TYPE IF EXISTS taskstatus")
    op.execute("DROP TYPE IF EXISTS tasktype")
    op.execute("DROP TYPE IF EXISTS triggertype")
    op.execute("DROP TYPE IF EXISTS runstatus")
    op.execute("DROP TYPE IF EXISTS activitytype")
    op.execute("DROP TYPE IF EXISTS coordinationstrategy")
    op.execute("DROP TYPE IF EXISTS agentspecialty")
    op.execute("DROP TYPE IF EXISTS missiontype")
    op.execute("DROP TYPE IF EXISTS missionstatus")
    op.execute("DROP TYPE IF EXISTS projecttype")
    op.execute("DROP TYPE IF EXISTS projectstatus")

    # ──────────────────────────────────────────────────────────────────────
    # PHASE 3: Restore archived tables
    # ──────────────────────────────────────────────────────────────────────
    for table in reversed(ARCHIVE_TABLES):
        op.execute(
            sa.text(
                f"ALTER TABLE IF EXISTS _archived_{table} RENAME TO {table}"
            )
        )

    # Restore indexes that were dropped
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_opportunities_source ON opportunities (source, source_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_call_campaigns_status ON call_campaigns (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_call_campaigns_scheduled_at ON call_campaigns (scheduled_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_call_campaigns_resend_email_id ON call_campaigns (resend_email_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_email_events_user_id ON email_events (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_email_events_campaign_id ON email_events (campaign_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_email_events_resend_email_id ON email_events (resend_email_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_email_events_event_type ON email_events (event_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_email_suppressions_email ON email_suppressions (email)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_matches_pipeline_stage ON matches (pipeline_stage)")
