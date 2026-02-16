"""Update enum values to lowercase, add new TODO statuses, add notification completion fields.

The initial migration created PostgreSQL enums using Python enum .name (uppercase)
instead of .value (lowercase). This migration recreates the enum types with correct
lowercase values and adds the new TODO statuses (open, in_progress, blocked, complete)
and notification completion columns.

Revision ID: a1b2c3d4e5f6
Revises: 93fb3e33a601
Create Date: 2026-02-16 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "93fb3e33a601"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Mapping: old uppercase name → new lowercase value
_TODO_STATUS_MAP = {"ACTIVE": "open", "COMPLETED": "complete", "DEFERRED": "deferred"}
_MEMORY_TYPE_MAP = {"EXPLICIT": "explicit", "INFERRED": "inferred", "EPISODIC": "episodic"}
_PRIORITY_SOURCE_MAP = {"INFERRED": "inferred", "USER_SET": "user_set"}


def _recreate_enum(
    table: str,
    column: str,
    enum_name: str,
    new_values: list[str],
    value_map: dict[str, str],
) -> None:
    """Recreate a PostgreSQL enum type with new values, migrating existing data."""
    tmp = f"{enum_name}_new"
    # Create the new enum type
    op.execute(f"CREATE TYPE {tmp} AS ENUM ({', '.join(repr(v) for v in new_values)})")
    # Migrate column: cast through text, mapping old values to new
    case_clauses = " ".join(
        f"WHEN '{old}' THEN '{new}'" for old, new in value_map.items()
    )
    op.execute(
        f"ALTER TABLE {table} ALTER COLUMN {column} TYPE {tmp} "
        f"USING (CASE {column}::text {case_clauses} ELSE {column}::text END)::{tmp}"
    )
    # Drop old type, rename new to old
    op.execute(f"DROP TYPE {enum_name}")
    op.execute(f"ALTER TYPE {tmp} RENAME TO {enum_name}")


def upgrade() -> None:
    # --- Recreate todostatus with lowercase values + new statuses ---
    _recreate_enum(
        table="todos",
        column="status",
        enum_name="todostatus",
        new_values=["open", "in_progress", "blocked", "complete", "deferred"],
        value_map=_TODO_STATUS_MAP,
    )

    # --- Recreate memorytype with lowercase values ---
    _recreate_enum(
        table="memories",
        column="type",
        enum_name="memorytype",
        new_values=["explicit", "inferred", "episodic"],
        value_map=_MEMORY_TYPE_MAP,
    )

    # --- Recreate prioritysource with lowercase values ---
    _recreate_enum(
        table="todos",
        column="priority_source",
        enum_name="prioritysource",
        new_values=["inferred", "user_set"],
        value_map=_PRIORITY_SOURCE_MAP,
    )

    # --- Add notification completion columns ---
    op.add_column(
        "notifications",
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "notifications",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    # --- Remove notification completion columns ---
    op.drop_column("notifications", "completed_at")
    op.drop_column("notifications", "completed")

    # --- Restore prioritysource to uppercase ---
    _recreate_enum(
        table="todos",
        column="priority_source",
        enum_name="prioritysource",
        new_values=["INFERRED", "USER_SET"],
        value_map={v: k for k, v in _PRIORITY_SOURCE_MAP.items()},
    )

    # --- Restore memorytype to uppercase ---
    _recreate_enum(
        table="memories",
        column="type",
        enum_name="memorytype",
        new_values=["EXPLICIT", "INFERRED", "EPISODIC"],
        value_map={v: k for k, v in _MEMORY_TYPE_MAP.items()},
    )

    # --- Restore todostatus to uppercase (new statuses map to closest old value) ---
    _recreate_enum(
        table="todos",
        column="status",
        enum_name="todostatus",
        new_values=["ACTIVE", "COMPLETED", "DEFERRED"],
        value_map={
            "open": "ACTIVE",
            "in_progress": "ACTIVE",
            "blocked": "ACTIVE",
            "complete": "COMPLETED",
            "deferred": "DEFERRED",
        },
    )
