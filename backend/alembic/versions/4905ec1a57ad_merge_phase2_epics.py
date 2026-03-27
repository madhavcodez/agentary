"""merge_phase2_epics

Revision ID: 4905ec1a57ad
Revises: 57d54c29f968, c3d4e5f6a7b8
Create Date: 2026-03-26 13:08:55.412365

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4905ec1a57ad'
down_revision: Union[str, None] = ('57d54c29f968', 'c3d4e5f6a7b8')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
