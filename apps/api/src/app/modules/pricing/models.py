import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    desc,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.pricing.rules import Rounding, TableMode


class _Withdrawable:
    """Rows that carry money are never edited: a correction withdraws the row (with a reason
    once the contract is published) and records a new one (ADR 0007)."""

    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    withdrawn_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    withdraw_reason: Mapped[str | None] = mapped_column(Text)


class PriceTable(_Withdrawable, UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A price table printed in one signed document of a contract."""

    __tablename__ = "price_tables"
    __table_args__ = (Index("ix_price_tables_contract_id", "contract_id"),)

    contract_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contracts.id", ondelete="CASCADE"))
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contract_instruments.id", ondelete="CASCADE")
    )
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    mode: Mapped[TableMode] = mapped_column(String(16))
    page: Mapped[int] = mapped_column(Integer)
    quote: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)


class PriceLine(_Withdrawable, UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "price_lines"
    __table_args__ = (Index("ix_price_lines_table_id", "table_id"),)

    table_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("price_tables.id", ondelete="CASCADE"))
    service: Mapped[str] = mapped_column(String(200))
    origin: Mapped[str | None] = mapped_column(String(200))
    destination: Mapped[str | None] = mapped_column(String(200))
    vehicle: Mapped[str | None] = mapped_column(String(100))
    unit: Mapped[str] = mapped_column(String(50))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3))
    # What the paper says about VAT; None when it says nothing.
    includes_vat: Mapped[bool | None] = mapped_column(Boolean)
    page: Mapped[int] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(Text)


class FuelClause(_Withdrawable, UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The fuel adjustment clause as one document states it; a later document resets the base."""

    __tablename__ = "fuel_clauses"
    __table_args__ = (Index("ix_fuel_clauses_contract_id", "contract_id"),)

    contract_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contracts.id", ondelete="CASCADE"))
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contract_instruments.id", ondelete="CASCADE")
    )
    fuel_type: Mapped[str] = mapped_column(String(100))
    base_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    base_on: Mapped[date] = mapped_column(Date)
    share: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    threshold: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    lag_days: Mapped[int] = mapped_column(Integer)
    rounding: Mapped[Rounding] = mapped_column(String(16))
    is_cumulative: Mapped[bool] = mapped_column(Boolean)
    page: Mapped[int] = mapped_column(Integer)
    quote: Mapped[str | None] = mapped_column(Text)


class FuelPrice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A published retail fuel price: synced from Petrolimex, or entered for a date before the sync."""

    __tablename__ = "fuel_prices"
    __table_args__ = (
        UniqueConstraint("fuel_type", "effective_on", name="uq_fuel_prices_type_date"),
        Index("ix_fuel_prices_created_at_id", desc("created_at"), desc("id")),
    )

    fuel_type: Mapped[str] = mapped_column(String(100))
    effective_on: Mapped[date] = mapped_column(Date)
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    source: Mapped[str | None] = mapped_column(Text)
    # Null when the price came from the Petrolimex sync rather than from a person.
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
