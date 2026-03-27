"""add index to monitor_runs.alert_id

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-26 14:01:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_monitor_runs_alert_id",
        "monitor_runs",
        ["alert_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_monitor_runs_alert_id", table_name="monitor_runs")
