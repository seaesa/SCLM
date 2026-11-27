import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    Connection,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    desc,
    event,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Partner(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A customer and/or supplier, mastered outside the CLM (ADR 0006). Every field except the
    id is overwritten by synchronization; contracts reference `id` only."""

    __tablename__ = "partners"
    __table_args__ = (
        Index("ix_partners_created_at_id", desc("created_at"), desc("id")),
        # Free-text search over code, name and legal name (`ILIKE '%…%'`).
        Index(
            "ix_partners_search_trgm",
            text("(lower(code || ' ' || name || ' ' || coalesce(legal_name, ''))) gin_trgm_ops"),
            postgresql_using="gin",
        ),
    )

    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    legal_name: Mapped[str | None] = mapped_column(String(500))
    tax_code: Mapped[str | None] = mapped_column(String(32), index=True)
    address: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(255))
    is_customer: Mapped[bool] = mapped_column(default=False)
    is_supplier: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    # Operations may run orders before the contract is signed (entry path C of the new-contract
    # process); the contracts module reads it, the source decides it.
    can_order_before_contract: Mapped[bool] = mapped_column(default=False)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # The accountant who looks after this partner; its contracts are theirs. Assigned in the
    # app, never by the sync, so a source update does not undo it.
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )


# The search index needs pg_trgm. Migrations create it explicitly; this covers `create_all`
# (tests), which does not run migrations.
@event.listens_for(Partner.__table__, "before_create")
def _create_trigram_extension(_table: Any, connection: Connection, **_: Any) -> None:
    connection.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS pg_trgm")


class PartnerExternalRef(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """How a source names a partner. `payload` is the record exactly as received, so any value
    shown in the CLM can be traced back to the source."""

    __tablename__ = "partner_external_refs"
    __table_args__ = (UniqueConstraint("source", "external_code"),)

    partner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("partners.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[str] = mapped_column(String(32))
    external_code: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ConflictKind(StrEnum):
    # Another partner already has this tax code; the two are never merged automatically.
    DUPLICATE_TAX_CODE = "duplicate_tax_code"
    # The same code carries different values in two exports (e.g. customer vs supplier file).
    SOURCE_MISMATCH = "source_mismatch"
    # The source no longer lists a partner the CLM knows; it is kept, contracts may use it.
    MISSING_FROM_SOURCE = "missing_from_source"


class PartnerConflict(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A data-quality problem found by synchronization, for an administrator to settle in the
    source. Sync closes it by itself once the problem is gone."""

    __tablename__ = "partner_conflicts"
    __table_args__ = (
        Index("ix_partner_conflicts_created_at_id", desc("created_at"), desc("id")),
        # At most one open conflict of a kind per partner: sync updates it instead of stacking.
        Index(
            "uq_partner_conflicts_open",
            "partner_id",
            "kind",
            unique=True,
            postgresql_where=text("resolved_at IS NULL"),
        ),
    )

    partner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("partners.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[ConflictKind] = mapped_column(String(32))
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    resolution_note: Mapped[str | None] = mapped_column(Text)
