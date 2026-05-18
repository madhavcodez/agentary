"""Performance indexes for mission status, findings, and dashboard queries.

Adds the indexes the parallel performance review identified as missing:
- ``ix_missions_status`` — backs ``GET /missions?status=...`` and the
  dashboard "running" filter; previously sequential scan.
- ``ix_missions_user_created`` — composite on ``(user_id, created_at DESC)``
  to back the dashboard's "your recent missions" query without a sort.
- ``ix_findings_mission_confidence`` — composite on
  ``(mission_id, confidence DESC)`` so finding lists per mission don't
  re-sort. The individual ``mission_id`` index stays (other queries use
  it on its own).

We deliberately do NOT use ``CREATE INDEX CONCURRENTLY`` here because
Alembic runs each migration inside a transaction and ``CONCURRENTLY``
cannot. For tables of this size (small for now) the locking impact is
trivial. If/when these tables grow to the point that index creation
blocks writes meaningfully, switch to running these via a one-off
maintenance script with autocommit.

Revision ID: f4a8d2c1e9b0
Revises: e3c7e5daf503
Create Date: 2026-05-17

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "f4a8d2c1e9b0"
down_revision: str | None = "e3c7e5daf503"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Postgres can scan B-tree indexes in either direction, so we don't need
    # explicit DESC ordering on the column list. The dashboard's
    # ``ORDER BY created_at DESC LIMIT N`` still uses the index efficiently.
    op.create_index(
        "ix_missions_status",
        "missions",
        ["status"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_missions_user_created",
        "missions",
        ["user_id", "created_at"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_findings_mission_confidence",
        "findings",
        ["mission_id", "confidence"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_findings_mission_confidence", table_name="findings")
    op.drop_index("ix_missions_user_created", table_name="missions")
    op.drop_index("ix_missions_status", table_name="missions")
