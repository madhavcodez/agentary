"""workflow_run_status_to_enum

Convert workflow_runs.status from varchar(20) to the existing runstatus enum.

Revision ID: a1b2c3d4e5f6
Revises: 779de7d32de8
Create Date: 2026-03-26 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "779de7d32de8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Normalise any legacy string values to valid enum members before casting.
    # "queued" is a valid RunStatus value, so most rows should already be fine.
    op.execute(
        """
        UPDATE workflow_runs
        SET status = 'created'
        WHERE status NOT IN (
            'created', 'queued', 'running', 'awaiting_input',
            'retrying', 'partially_failed', 'completed', 'failed', 'cancelled'
        )
        """
    )

    # Alter column type from varchar to the existing runstatus enum.
    op.execute(
        """
        ALTER TABLE workflow_runs
        ALTER COLUMN status TYPE runstatus
        USING status::runstatus
        """
    )

    # Set a proper default using the enum value.
    op.execute(
        """
        ALTER TABLE workflow_runs
        ALTER COLUMN status SET DEFAULT 'created'::runstatus
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE workflow_runs
        ALTER COLUMN status TYPE varchar(20)
        USING status::text
        """
    )
    op.execute(
        """
        ALTER TABLE workflow_runs
        ALTER COLUMN status SET DEFAULT 'queued'
        """
    )
