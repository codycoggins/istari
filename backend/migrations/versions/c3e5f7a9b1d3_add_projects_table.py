"""add projects table

Revision ID: c3e5f7a9b1d3
Revises: b2d4e6f8a0c2
Create Date: 2026-03-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3e5f7a9b1d3'
down_revision: Union[str, None] = 'b2d4e6f8a0c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create projects table WITHOUT next_action_id first (circular FK)
    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('goal', sa.Text(), nullable=True),
        sa.Column(
            'status',
            sa.Enum('active', 'paused', 'complete', name='projectstatus'),
            nullable=False,
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # Add project_id FK to todos
    op.add_column(
        'todos',
        sa.Column('project_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_todos_project_id',
        'todos', 'projects',
        ['project_id'], ['id'],
        ondelete='SET NULL',
    )

    # Now add next_action_id to projects (deferred circular FK)
    op.add_column(
        'projects',
        sa.Column('next_action_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_projects_next_action',
        'projects', 'todos',
        ['next_action_id'], ['id'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_projects_next_action', 'projects', type_='foreignkey')
    op.drop_column('projects', 'next_action_id')
    op.drop_constraint('fk_todos_project_id', 'todos', type_='foreignkey')
    op.drop_column('todos', 'project_id')
    op.drop_table('projects')
    op.execute("DROP TYPE IF EXISTS projectstatus")
