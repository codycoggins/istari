"""Project model — top-level container for related TODOs with a shared goal."""

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from istari.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from istari.models.todo import Todo


class ProjectStatus(enum.StrEnum):
    active = "active"
    paused = "paused"
    complete = "complete"


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    goal: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, values_callable=lambda e: [m.value for m in e]),
        default=ProjectStatus.active,
    )
    # Circular FK to todos.id — use_alter defers constraint creation
    next_action_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("todos.id", use_alter=True, name="fk_projects_next_action"),
        nullable=True,
    )

    # Relationships — forward references as strings to break circular import
    next_action: "Mapped[Todo | None]" = relationship(
        "Todo",
        foreign_keys=[next_action_id],
        lazy="select",
    )
    todos: "Mapped[list[Todo]]" = relationship(
        "Todo",
        back_populates="project",
        foreign_keys="[Todo.project_id]",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} name={self.name!r} status={self.status}>"
