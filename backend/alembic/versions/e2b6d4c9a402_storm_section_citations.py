"""STORM phase 2: section_citations table + reports.storm_generated flag.

Revision ID: e2b6d4c9a402
Revises: e1a5c2b8f301
Create Date: 2026-04-14 16:05:00.000000

Adds per-section citation bindings for STORM-generated reports and a
boolean on ``reports`` to distinguish STORM output from legacy synthesis.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e2b6d4c9a402"
down_revision: Union[str, None] = "e1a5c2b8f301"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "section_citations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("section_index", sa.Integer(), nullable=False),
        sa.Column("finding_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quote_span", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["finding_id"], ["findings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_section_citations_finding_id"),
        "section_citations",
        ["finding_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_section_citations_report_id"),
        "section_citations",
        ["report_id"],
        unique=False,
    )
    op.create_index(
        "ix_section_citations_report_section",
        "section_citations",
        ["report_id", "section_index"],
        unique=False,
    )

    op.add_column(
        "reports",
        sa.Column(
            "storm_generated",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("reports", "storm_generated")
    op.drop_index("ix_section_citations_report_section", table_name="section_citations")
    op.drop_index(
        op.f("ix_section_citations_report_id"), table_name="section_citations"
    )
    op.drop_index(
        op.f("ix_section_citations_finding_id"), table_name="section_citations"
    )
    op.drop_table("section_citations")
