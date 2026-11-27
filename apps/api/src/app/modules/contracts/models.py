import uuid
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    desc,
    false,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin


class InstrumentKind(StrEnum):
    CONTRACT = "contract"
    # Attached to the original contract (price table, KPI...): it changes no date.
    SCHEDULE = "schedule"
    ADDENDUM = "addendum"
    TERMINATION = "termination"


class ContractCategory(StrEnum):
    """The three kinds the business manages; each has its own code series."""

    CUSTOMER = "customer"
    CONTRACTOR = "contractor"
    WAREHOUSE = "warehouse"


CODE_PREFIXES: dict[ContractCategory, str] = {
    ContractCategory.CUSTOMER: "HĐKH",
    ContractCategory.CONTRACTOR: "HĐNT",
    ContractCategory.WAREHOUSE: "HĐTK",
}


class SigningState(StrEnum):
    UNSIGNED = "unsigned"
    SPIDER_SIGNED = "spider_signed"
    PARTNER_SIGNED = "partner_signed"
    # Signed and stamped by both parties: only now does the document count.
    SIGNED = "signed"


class ReviewState(StrEnum):
    """Approval of a document Spider drafts itself (a contract or an addendum). Archive documents
    and documents drafted by the counterparty are recorded after signing and have no review."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class EventKind(StrEnum):
    CREATED = "created"
    # A document recorded on the contract.
    ADDED = "added"
    # Facts of a document changed; `changes` holds each field's value before and after.
    EDITED = "edited"
    # Loaded from the scanned archive rather than recorded by a person.
    IMPORTED = "imported"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    SIGNING = "signing"
    # The document itself is gone; the comment keeps its code so the history still reads.
    DELETED = "deleted"


class Standing(StrEnum):
    """Where a signed addendum or schedule stands on a given day."""

    # Takes effect later.
    PENDING = "pending"
    # The latest one for the prices or the fuel base it sets: it is what applies now.
    APPLYING = "applying"
    # Its change (term, route, payment…) still holds while the contract runs.
    IN_FORCE = "in_force"
    # A later document set the same prices or fuel base.
    SUPERSEDED = "superseded"
    # Its own end date passed, or the contract no longer runs.
    LAPSED = "lapsed"
    # A later addendum annulled it.
    REVOKED = "revoked"


class Contract(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A contract with one partner and the documents that change it. Its facts live in field
    values; the signed paper stays the reference, the system keeps what is needed to manage it."""

    __tablename__ = "contracts"
    __table_args__ = (
        Index("ix_contracts_created_at_id", desc("created_at"), desc("id")),
        Index("ix_contracts_partner_id", "partner_id"),
        Index("ix_contracts_dossier_id", "dossier_id"),
        Index("ix_contracts_status", "status"),
        Index("ix_contracts_end_on", "end_on"),
        Index("ix_contracts_effective_from", "effective_from"),
        Index("ix_contracts_signed_on", "signed_on"),
        Index("ix_contracts_notice_on", "notice_on"),
        Index("ix_contracts_code", "code", unique=True),
        Index("ix_contracts_missing_count", "missing_count"),
        Index("ix_contracts_renewal", "renewal"),
        Index("ix_contracts_replaced_by_id", "replaced_by_id"),
    )

    partner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("partners.id", ondelete="RESTRICT"))
    side: Mapped[str] = mapped_column(String(16))
    category: Mapped[ContractCategory] = mapped_column(String(16))
    # Issued when the contract is recorded: type, year, running number (HĐKH-2026-0001).
    code: Mapped[str | None] = mapped_column(String(32))
    # Every signed file of the contract is in this dossier.
    dossier_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_sets.id", ondelete="RESTRICT")
    )
    # A re-signed contract: the one that took its place, and the day it did.
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("contracts.id", ondelete="SET NULL")
    )
    replaced_on: Mapped[date | None] = mapped_column(Date)
    # Loaded from the scanned archive: kept even when nothing of it was approved or signed here.
    is_imported: Mapped[bool] = mapped_column(Boolean, server_default=false())
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    # Copies of what the facts say today, kept so tables can filter, sort and count in SQL.
    # Refreshed on every change and each night, when the date moves (ContractService.refresh).
    number: Mapped[str | None] = mapped_column(String(255))
    signed_on: Mapped[date | None] = mapped_column(Date)
    effective_from: Mapped[date | None] = mapped_column(Date)
    end_on: Mapped[date | None] = mapped_column(Date)
    # Last day to tell the partner the contract will not be renewed (end minus notice days).
    notice_on: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(32), server_default="draft")
    missing_count: Mapped[int] = mapped_column(Integer, server_default="0")
    # The renewal clause of the contract document (none, automatic, conditional).
    renewal: Mapped[str | None] = mapped_column(String(16))
    # The credit terms in force, copied for the list's column and filters.
    payment_days: Mapped[int | None] = mapped_column(Integer)
    payment_from: Mapped[str | None] = mapped_column(String(16))
    statement_cutoff: Mapped[str | None] = mapped_column(String(16))


class CodeCounter(Base):
    """Last number issued per code prefix and year."""

    __tablename__ = "contract_code_counters"

    prefix: Mapped[str] = mapped_column(String(16), primary_key=True)
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_number: Mapped[int] = mapped_column(Integer)


class Instrument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One signed document of a contract. Its printed number is the `number` field, kept as text
    because papers use forms like 01A, 02.01 or a repeated number."""

    __tablename__ = "contract_instruments"
    __table_args__ = (
        Index("ix_contract_instruments_contract_id", "contract_id"),
        Index("ix_contract_instruments_review_state", "review_state"),
        Index("ix_contract_instruments_code", "code", unique=True),
        Index("ix_contract_instruments_effective_from", "effective_from"),
    )

    contract_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contracts.id", ondelete="CASCADE"))
    kind: Mapped[InstrumentKind] = mapped_column(String(16))
    # Addenda and schedules: the contract code plus PL01, PL02... in the order they are recorded.
    code: Mapped[str | None] = mapped_column(String(48))
    # Null when nobody at Spider has to approve it (archive, counterparty's draft).
    review_state: Mapped[ReviewState | None] = mapped_column(String(16))
    signing_state: Mapped[SigningState] = mapped_column(String(16), server_default="signed")
    # The draft while it is being approved and signed, then the signed scan.
    file_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("document_files.id", ondelete="RESTRICT"))
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    # Copies of current values, kept so the list of addenda can filter and sort across
    # contracts; refreshed whenever the contract is (`ContractService._store_derived`).
    number: Mapped[str | None] = mapped_column(String(128))
    signed_on: Mapped[date | None] = mapped_column(Date)
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    # Comma-joined adjustment kinds.
    adjustments: Mapped[str | None] = mapped_column(String(128))
    summary: Mapped[str | None] = mapped_column(Text)
    missing_count: Mapped[int] = mapped_column(Integer, server_default="0")
    # Settled addenda and schedules only; recomputed nightly, since it moves with the date.
    standing: Mapped[Standing | None] = mapped_column(String(16))
    # The document that superseded or revoked this one.
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("contract_instruments.id", ondelete="SET NULL")
    )


class FieldValue(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One value of one field on one document. A change supersedes the current value instead of
    overwriting it, so the history of who entered what is kept."""

    __tablename__ = "contract_field_values"
    __table_args__ = (
        Index("ix_contract_field_values_instrument_key", "instrument_id", "key"),
        Index(
            "uq_contract_field_values_current",
            "instrument_id",
            "key",
            unique=True,
            postgresql_where=text("superseded_at IS NULL"),
        ),
    )

    instrument_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contract_instruments.id", ondelete="CASCADE")
    )
    key: Mapped[str] = mapped_column(String(64))
    # Normalized text: ISO date, integer, a choice code; None records that the field was cleared.
    value: Mapped[str | None] = mapped_column(Text)
    entered_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ContractEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Append-only history: who created, submitted, approved, rejected or signed, with which file."""

    __tablename__ = "contract_events"
    __table_args__ = (Index("ix_contract_events_contract_id", "contract_id", "created_at"),)

    contract_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contracts.id", ondelete="CASCADE"))
    # Kept when the document is deleted, so the history still says what happened to it.
    instrument_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("contract_instruments.id", ondelete="SET NULL")
    )
    instrument_code: Mapped[str | None] = mapped_column(String(64))
    kind: Mapped[EventKind] = mapped_column(String(16))
    changes: Mapped[list[dict[str, str | None]] | None] = mapped_column(JSONB)
    # The draft that was submitted or approved: the signed copy is checked against it.
    file_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("document_files.id", ondelete="RESTRICT")
    )
    comment: Mapped[str | None] = mapped_column(Text)
    # For a signing event: the state reached.
    signing_state: Mapped[SigningState | None] = mapped_column(String(16))
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
