"""merge_phase1_fixes_and_phase2_models

Revision ID: 57d54c29f968
Revises: a2b5b89026e6, b2c3d4e5f6a7
Create Date: 2026-03-26 12:58:13.995774

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '57d54c29f968'
down_revision: Union[str, None] = ('a2b5b89026e6', 'b2c3d4e5f6a7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
