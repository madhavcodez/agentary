"""add_run_lifecycle_state_machine

Revision ID: 9c0c284877e1
Revises: 009
Create Date: 2026-03-26 11:40:24.023927

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9c0c284877e1'
down_revision: Union[str, None] = '009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- 1. Extend existing 'runstatus' enum with new lifecycle values --
    # The enum already has: queued, running, completed, failed, cancelled
    # We need to add: created, awaiting_input, retrying, partially_failed
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction, so we need
    # to commit the current transaction first.
    conn = op.get_bind()
    conn.execute(sa.text("COMMIT"))
    conn.execute(sa.text("ALTER TYPE runstatus ADD VALUE IF NOT EXISTS 'created' BEFORE 'queued'"))
    conn.execute(sa.text("ALTER TYPE runstatus ADD VALUE IF NOT EXISTS 'awaiting_input' AFTER 'running'"))
    conn.execute(sa.text("ALTER TYPE runstatus ADD VALUE IF NOT EXISTS 'retrying' AFTER 'awaiting_input'"))
    conn.execute(sa.text("ALTER TYPE runstatus ADD VALUE IF NOT EXISTS 'partially_failed' AFTER 'retrying'"))
    conn.execute(sa.text("BEGIN"))

    # -- 2. Create failurecategory enum (does not exist yet) --
    failurecategory = postgresql.ENUM(
        'transient_connector', 'model_error', 'rate_limited', 'timeout',
        'validation', 'internal', 'cancelled',
        name='failurecategory', create_type=False,
    )
    failurecategory.create(op.get_bind(), checkfirst=True)

    # -- 3. Create monitor_runs table (uses pre-existing enums) --
    op.create_table('monitor_runs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('monitor_id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=True),
        sa.Column('status', postgresql.ENUM(
            'created', 'queued', 'running', 'awaiting_input', 'retrying',
            'partially_failed', 'completed', 'failed', 'cancelled',
            name='runstatus', create_type=False,
        ), nullable=False, server_default='created'),
        sa.Column('failure_category', postgresql.ENUM(
            'transient_connector', 'model_error', 'rate_limited', 'timeout',
            'validation', 'internal', 'cancelled',
            name='failurecategory', create_type=False,
        ), nullable=True),
        sa.Column('failure_message', sa.Text(), nullable=True),
        sa.Column('state_transitions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('correlation_id', sa.UUID(), nullable=True),
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('alert_id', sa.UUID(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['alert_id'], ['alerts.id']),
        sa.ForeignKeyConstraint(['monitor_id'], ['monitors.id']),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_monitor_runs_correlation_id'), 'monitor_runs', ['correlation_id'], unique=False)
    op.create_index(op.f('ix_monitor_runs_monitor_id'), 'monitor_runs', ['monitor_id'], unique=False)
    op.create_index(op.f('ix_monitor_runs_project_id'), 'monitor_runs', ['project_id'], unique=False)

    # NOTE: Legacy tables (email_events, matches, call_campaigns, etc.) exist in
    # the database but are not modeled in the current codebase. We intentionally
    # skip dropping them to preserve data.

    # -- 4. Add lifecycle columns to call_records --
    op.add_column('call_records', sa.Column('failure_category', postgresql.ENUM(name='failurecategory', create_type=False), nullable=True))
    op.add_column('call_records', sa.Column('failure_message', sa.Text(), nullable=True))
    op.add_column('call_records', sa.Column('state_transitions', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('call_records', sa.Column('correlation_id', sa.UUID(), nullable=True))
    op.create_index(op.f('ix_call_records_correlation_id'), 'call_records', ['correlation_id'], unique=False)

    # -- 5. Add lifecycle columns to mission_runs --
    op.add_column('mission_runs', sa.Column('failure_category', postgresql.ENUM(name='failurecategory', create_type=False), nullable=True))
    op.add_column('mission_runs', sa.Column('failure_message', sa.Text(), nullable=True))
    op.add_column('mission_runs', sa.Column('state_transitions', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('mission_runs', sa.Column('retry_count', sa.Integer(), nullable=True))
    op.add_column('mission_runs', sa.Column('max_retries', sa.Integer(), nullable=True))
    op.add_column('mission_runs', sa.Column('correlation_id', sa.UUID(), nullable=True))
    op.add_column('mission_runs', sa.Column('idempotency_key', sa.String(length=255), nullable=True))
    op.create_index(op.f('ix_mission_runs_correlation_id'), 'mission_runs', ['correlation_id'], unique=False)
    op.create_unique_constraint('uq_mission_runs_idempotency_key', 'mission_runs', ['idempotency_key'])

    # -- 6. Add lifecycle columns to reports --
    op.add_column('reports', sa.Column('failure_category', postgresql.ENUM(name='failurecategory', create_type=False), nullable=True))
    op.add_column('reports', sa.Column('failure_message', sa.Text(), nullable=True))
    op.add_column('reports', sa.Column('state_transitions', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('reports', sa.Column('correlation_id', sa.UUID(), nullable=True))
    op.create_index(op.f('ix_reports_correlation_id'), 'reports', ['correlation_id'], unique=False)

    # -- 7. Add lifecycle columns to workflow_runs --
    op.add_column('workflow_runs', sa.Column('failure_category', postgresql.ENUM(name='failurecategory', create_type=False), nullable=True))
    op.add_column('workflow_runs', sa.Column('failure_message', sa.Text(), nullable=True))
    op.add_column('workflow_runs', sa.Column('state_transitions', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('workflow_runs', sa.Column('retry_count', sa.Integer(), nullable=True))
    op.add_column('workflow_runs', sa.Column('max_retries', sa.Integer(), nullable=True))
    op.add_column('workflow_runs', sa.Column('correlation_id', sa.UUID(), nullable=True))
    op.add_column('workflow_runs', sa.Column('idempotency_key', sa.String(length=255), nullable=True))
    op.create_index(op.f('ix_workflow_runs_correlation_id'), 'workflow_runs', ['correlation_id'], unique=False)
    op.create_unique_constraint('uq_workflow_runs_idempotency_key', 'workflow_runs', ['idempotency_key'])


def downgrade() -> None:
    # -- workflow_runs --
    op.drop_constraint('uq_workflow_runs_idempotency_key', 'workflow_runs', type_='unique')
    op.drop_index(op.f('ix_workflow_runs_correlation_id'), table_name='workflow_runs')
    op.drop_column('workflow_runs', 'idempotency_key')
    op.drop_column('workflow_runs', 'correlation_id')
    op.drop_column('workflow_runs', 'max_retries')
    op.drop_column('workflow_runs', 'retry_count')
    op.drop_column('workflow_runs', 'state_transitions')
    op.drop_column('workflow_runs', 'failure_message')
    op.drop_column('workflow_runs', 'failure_category')

    # -- reports --
    op.drop_index(op.f('ix_reports_correlation_id'), table_name='reports')
    op.drop_column('reports', 'correlation_id')
    op.drop_column('reports', 'state_transitions')
    op.drop_column('reports', 'failure_message')
    op.drop_column('reports', 'failure_category')

    # -- mission_runs --
    op.drop_constraint('uq_mission_runs_idempotency_key', 'mission_runs', type_='unique')
    op.drop_index(op.f('ix_mission_runs_correlation_id'), table_name='mission_runs')
    op.drop_column('mission_runs', 'idempotency_key')
    op.drop_column('mission_runs', 'correlation_id')
    op.drop_column('mission_runs', 'max_retries')
    op.drop_column('mission_runs', 'retry_count')
    op.drop_column('mission_runs', 'state_transitions')
    op.drop_column('mission_runs', 'failure_message')
    op.drop_column('mission_runs', 'failure_category')

    # -- call_records --
    op.drop_index(op.f('ix_call_records_correlation_id'), table_name='call_records')
    op.drop_column('call_records', 'correlation_id')
    op.drop_column('call_records', 'state_transitions')
    op.drop_column('call_records', 'failure_message')
    op.drop_column('call_records', 'failure_category')

    # -- monitor_runs --
    op.drop_index(op.f('ix_monitor_runs_project_id'), table_name='monitor_runs')
    op.drop_index(op.f('ix_monitor_runs_monitor_id'), table_name='monitor_runs')
    op.drop_index(op.f('ix_monitor_runs_correlation_id'), table_name='monitor_runs')
    op.drop_table('monitor_runs')

    # -- Drop failurecategory enum type --
    op.execute("DROP TYPE IF EXISTS failurecategory")

    # NOTE: We do NOT remove enum values from runstatus as PostgreSQL does
    # not support removing enum values. The extra values are harmless.
