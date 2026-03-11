"""TODO model — Istari is the system of record for TODOs."""

import datetime
import enum
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from istari.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from istari.models.project import Project


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
    today_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    last_prompted_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768))
    project_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    project: Mapped["Project | None"] = relationship(
        "Project",
        back_populates="todos",
        foreign_keys=[project_id],
        lazy="select",
    )
