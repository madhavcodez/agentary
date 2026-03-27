"""add merge_history table for entity merge undo support

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-26 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "merge_history",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("primary_entity_id", sa.UUID(), nullable=False),
        sa.Column("merged_entity_id", sa.UUID(), nullable=False),
        sa.Column(
            "merged_entity_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "merged_aliases",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=True,
        ),
        sa.Column(
            "merged_observations_count",
            sa.Integer(),
            server_default="0",
            nullable=True,
        ),
        sa.Column(
            "is_undone",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["primary_entity_id"], ["entities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_merge_history_project_id",
        "merge_history",
        ["project_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_merge_history_project_id", table_name="merge_history")
    op.drop_table("merge_history")
