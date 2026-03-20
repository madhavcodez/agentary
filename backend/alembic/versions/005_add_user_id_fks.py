"""Add user_id foreign keys to all data tables for multi-tenancy

Revision ID: 005
Revises: 004
Create Date: 2026-03-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None

# Default user UUID for backfilling existing rows during migration.
# This allows the column to become NOT NULL without violating constraints.
DEFAULT_USER_UUID = "00000000-0000-0000-0000-000000000000"

# All data tables that require user_id scoping.
TABLES = [
    "profiles",
    "opportunities",
    "matches",
    "contacts",
    "call_campaigns",
    "call_logs",
    "dossiers",
    "policies",
    "research_results",
    "action_logs",
]


def upgrade() -> None:
    # Ensure the default user exists so the FK constraint is satisfied.
    op.execute(
        sa.text(
            "INSERT INTO users (id, email, password_hash, name, is_active, created_at, updated_at) "
            "VALUES (:id, :email, :pw, :name, true, now(), now()) "
            "ON CONFLICT (id) DO NOTHING"
        ).bindparams(
            id=DEFAULT_USER_UUID,
            email="migration-default@secretairy.internal",
            pw="!MIGRATION_PLACEHOLDER_NOT_A_REAL_HASH!",
            name="Migration Default",
        )
    )

    for table in TABLES:
        # Step 1: Add column as nullable
        op.add_column(
            table,
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        )

        # Step 2: Backfill existing rows with the default user
        op.execute(
            sa.text(f"UPDATE {table} SET user_id = :uid WHERE user_id IS NULL").bindparams(
                uid=DEFAULT_USER_UUID,
            )
        )

        # Step 3: Alter column to NOT NULL
        op.alter_column(table, "user_id", nullable=False)

        # Step 4: Add foreign key constraint
        op.create_foreign_key(
            f"fk_{table}_user_id",
            table,
            "users",
            ["user_id"],
            ["id"],
        )

        # Step 5: Add index on user_id for filtering
        op.create_index(f"ix_{table}_user_id", table, ["user_id"])

        # Step 6: Add composite index on (user_id, created_at) for common queries
        op.create_index(
            f"ix_{table}_user_id_created_at",
            table,
            ["user_id", "created_at"],
        )


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_index(f"ix_{table}_user_id_created_at", table_name=table)
        op.drop_index(f"ix_{table}_user_id", table_name=table)
        op.drop_constraint(f"fk_{table}_user_id", table, type_="foreignkey")
        op.drop_column(table, "user_id")

    # Remove the migration default user
    op.execute(
        sa.text("DELETE FROM users WHERE id = :id").bindparams(id=DEFAULT_USER_UUID)
    )
