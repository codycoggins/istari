"""Digest model — stores processed digests from Gmail, Calendar, etc."""

import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from istari.models.base import Base, TimestampMixin


class Digest(TimestampMixin, Base):
    __tablename__ = "digests"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(50))
    content_summary: Mapped[str] = mapped_column(Text)
    items_json: Mapped[dict[str, object] | None] = mapped_column(JSON)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
