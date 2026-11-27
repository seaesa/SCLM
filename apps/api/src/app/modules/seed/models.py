from typing import Any

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SeedRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The last successful run of one seed step: a step whose input has not changed since is
    skipped, so the seed can be run on every deploy."""

    __tablename__ = "seed_runs"

    step: Mapped[str] = mapped_column(String(32), unique=True)
    checksum: Mapped[str] = mapped_column(String(64))
    report: Mapped[dict[str, Any]] = mapped_column(JSONB)
