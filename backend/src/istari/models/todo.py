"""TODO model — Istari is the system of record for TODOs."""

import datetime
import enum

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from istari.models.base import Base, TimestampMixin


class TodoStatus(enum.StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETE = "complete"
    DEFERRED = "deferred"


class PrioritySource(enum.StrEnum):
    INFERRED = "inferred"
    USER_SET = "user_set"


class Todo(TimestampMixin, Base):
    __tablename__ = "todos"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    body: Mapped[str | None] = mapped_column(Text)
    status: Mapped[TodoStatus] = mapped_column(
        Enum(TodoStatus, values_callable=lambda e: [m.value for m in e]),
        default=TodoStatus.OPEN,
    )
    priority: Mapped[int | None] = mapped_column()
    priority_source: Mapped[PrioritySource | None] = mapped_column(
        Enum(PrioritySource, values_callable=lambda e: [m.value for m in e]),
    )
    urgent: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    important: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    source: Mapped[str | None] = mapped_column(String(100))
    source_link: Mapped[str | None] = mapped_column(String(1000))
    due_date: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    last_prompted_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768))
