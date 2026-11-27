import uuid
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DocumentSide(StrEnum):
    CUSTOMER = "customer"
    SUPPLIER = "supplier"


class DocumentFile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One stored file, identified by its bytes. The same scan filed in two places is one row."""

    __tablename__ = "document_files"

    sha256: Mapped[str] = mapped_column(String(64), unique=True)
    storage_key: Mapped[str] = mapped_column(String(128))
    size: Mapped[int] = mapped_column(BigInteger)
    content_type: Mapped[str] = mapped_column(String(128))


class DocumentSet(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The files of one contract: a partner's archive papers, or what is attached from now on."""

    __tablename__ = "document_sets"
    __table_args__ = (Index("ix_document_sets_partner_id", "partner_id"),)

    # "archive/<key>" for the seeded archive, "contract/<uuid>" for a contract made here.
    source_path: Mapped[str] = mapped_column(Text, unique=True)
    side: Mapped[DocumentSide] = mapped_column(String(16))
    file_count: Mapped[int] = mapped_column(Integer)
    # Null only for archive papers no partner could be found for.
    partner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("partners.id", ondelete="RESTRICT")
    )


class DocumentSetFile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_set_files"
    __table_args__ = (
        UniqueConstraint("set_id", "path"),
        Index("ix_document_set_files_file_id", "file_id"),
    )

    set_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("document_sets.id", ondelete="CASCADE"))
    file_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("document_files.id", ondelete="RESTRICT"))
    # Where the file was filed in the scanned archive (relative to its root), or its upload name.
    path: Mapped[str] = mapped_column(Text)
