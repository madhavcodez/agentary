"""add last_error and last_error_at to monitors

Revision ID: 6f361779c4d0
Revises: 9c0c284877e1
Create Date: 2026-03-26 11:53:03.816548

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6f361779c4d0'
down_revision: Union[str, None] = '9c0c284877e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('monitors', sa.Column('last_error', sa.Text(), nullable=True))
    op.add_column('monitors', sa.Column('last_error_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('monitors', 'last_error_at')
    op.drop_column('monitors', 'last_error')
