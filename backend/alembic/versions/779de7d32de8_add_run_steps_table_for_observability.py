"""add run_steps table for observability

Revision ID: 779de7d32de8
Revises: 6f361779c4d0
Create Date: 2026-03-26 12:02:58.612453

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '779de7d32de8'
down_revision: Union[str, None] = '6f361779c4d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('run_steps',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('run_id', sa.UUID(), nullable=False),
        sa.Column('run_type', sa.String(length=50), nullable=False),
        sa.Column('correlation_id', sa.UUID(), nullable=True),
        sa.Column('step_type', sa.Enum(
            'expert_task', 'tool_call', 'synthesis',
            'node_execution', 'api_call', 'signal_processing',
            name='steptype',
        ), nullable=False),
        sa.Column('step_name', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('input_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('output_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('cost_usd', sa.Float(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('parent_step_id', sa.UUID(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['parent_step_id'], ['run_steps.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_run_steps_correlation_id'), 'run_steps', ['correlation_id'], unique=False)
    op.create_index(op.f('ix_run_steps_run_id'), 'run_steps', ['run_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_run_steps_run_id'), table_name='run_steps')
    op.drop_index(op.f('ix_run_steps_correlation_id'), table_name='run_steps')
    op.drop_table('run_steps')
