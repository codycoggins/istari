"""add recurrence_rule to todos

Revision ID: d4f6a8b2c1e3
Revises: c3e5f7a9b1d3
Create Date: 2026-03-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4f6a8b2c1e3'
down_revision: Union[str, None] = 'c3e5f7a9b1d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'todos',
        sa.Column('recurrence_rule', sa.String(length=200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('todos', 'recurrence_rule')
