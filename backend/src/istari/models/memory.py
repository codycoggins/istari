"""Memory model — explicit, inferred, and episodic memory types."""

import enum

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Enum, Float, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from istari.models.base import Base, TimestampMixin


class MemoryType(str, enum.Enum):
    EXPLICIT = "explicit"
    INFERRED = "inferred"
    EPISODIC = "episodic"


class Memory(TimestampMixin, Base):
    __tablename__ = "memories"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[MemoryType] = mapped_column(Enum(MemoryType))
    content: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    last_referenced_at: Mapped[None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_contradicted_at: Mapped[None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str | None] = mapped_column(String(100))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))
