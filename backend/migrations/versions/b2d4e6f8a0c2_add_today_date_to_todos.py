"""add today_date to todos

Revision ID: b2d4e6f8a0c2
Revises: a1ca9dbbef4a
Create Date: 2026-03-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2d4e6f8a0c2'
down_revision: Union[str, None] = '03aeaee79ef9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('todos', sa.Column('today_date', sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column('todos', 'today_date')
