"""add_hnsw_index_on_memories_embedding

Revision ID: 03aeaee79ef9
Revises: a1ca9dbbef4a
Create Date: 2026-02-25 18:27:33.688913

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '03aeaee79ef9'
down_revision: Union[str, None] = 'a1ca9dbbef4a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_memories_embedding_hnsw "
        "ON memories USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_memories_embedding_hnsw")
