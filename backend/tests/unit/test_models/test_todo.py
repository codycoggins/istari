"""Model enum tests — verify enum wiring and PostgreSQL compatibility."""

import enum

from sqlalchemy import Enum as SAEnum

import istari.models  # noqa: F401 — registers all models on Base.metadata
from istari.models.base import Base
from istari.models.todo import TodoStatus


def test_todo_status_values():
    assert TodoStatus.OPEN == "open"
    assert TodoStatus.IN_PROGRESS == "in_progress"
    assert TodoStatus.BLOCKED == "blocked"
    assert TodoStatus.COMPLETE == "complete"
    assert TodoStatus.DEFERRED == "deferred"


def test_enum_columns_use_values_not_names():
    """SQLAlchemy Enum() defaults to member .name (uppercase) for DB storage.

    With StrEnum, .name is e.g. "OPEN" but .value is "open". PostgreSQL
    native enums are case-sensitive, so sending "OPEN" when the type expects
    "open" causes InvalidTextRepresentationError. Every Enum column must use
    values_callable to send .value instead.
    """
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if not isinstance(column.type, SAEnum) or column.type.enum_class is None:
                continue
            py_enum = column.type.enum_class
            if not issubclass(py_enum, enum.StrEnum):
                continue
            sa_enums = sorted(column.type.enums)
            expected = sorted(m.value for m in py_enum)
            assert sa_enums == expected, (
                f"{table.name}.{column.name}: SQLAlchemy enum stores {sa_enums} "
                f"but Python enum values are {expected}. "
                f"Add values_callable=lambda e: [m.value for m in e] to Enum()."
            )
