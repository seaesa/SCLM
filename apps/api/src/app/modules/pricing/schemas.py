import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import Field, computed_field

from app.modules.pricing.rules import Rounding, TableMode
from app.shared.pagination import PageParams
from app.shared.schemas import Schema


class WithdrawRequest(Schema):
    # Required once the contract is published.
    reason: str | None = Field(default=None, min_length=3, max_length=1000)


class PriceTableWrite(Schema):
    instrument_id: uuid.UUID
    effective_from: date
    effective_to: date | None = None
    mode: TableMode
    page: int = Field(ge=1)
    quote: str | None = Field(default=None, max_length=2000)
    note: str | None = Field(default=None, max_length=2000)


class PriceLineWrite(Schema):
    service: str = Field(min_length=1, max_length=200)
    origin: str | None = Field(default=None, max_length=200)
    destination: str | None = Field(default=None, max_length=200)
    vehicle: str | None = Field(default=None, max_length=100)
    unit: str = Field(min_length=1, max_length=50)
    unit_price: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: str = Field(default="VND", pattern=r"^[A-Z]{3}$")
    includes_vat: bool | None = None
    page: int = Field(ge=1)
    note: str | None = Field(default=None, max_length=2000)


class PriceLinesCreate(Schema):
    lines: list[PriceLineWrite] = Field(min_length=1, max_length=500)


class PriceLineCorrection(PriceLineWrite):
    reason: str | None = Field(default=None, min_length=3, max_length=1000)


class PriceLineRead(Schema):
    id: uuid.UUID
    table_id: uuid.UUID
    service: str
    origin: str | None
    destination: str | None
    vehicle: str | None
    unit: str
    unit_price: Decimal
    currency: str
    includes_vat: bool | None
    page: int
    note: str | None
    created_at: datetime


class PriceTableSummary(Schema):
    id: uuid.UUID
    contract_id: uuid.UUID
    instrument_id: uuid.UUID
    effective_from: date
    effective_to: date | None
    mode: TableMode
    page: int
    quote: str | None
    note: str | None
    created_at: datetime


class ComparedLineRead(PriceLineRead):
    """A line with the price it replaced, for the before/after view of an addendum."""

    previous_price: Decimal | None
    # Fraction, 0.05 = +5%. None for a new route or a first price table.
    change: Decimal | None


class PriceTableRead(PriceTableSummary):
    lines: list[ComparedLineRead]


class FuelClauseWrite(Schema):
    instrument_id: uuid.UUID
    fuel_type: str = Field(min_length=1, max_length=100)
    base_price: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    base_on: date
    share: Decimal = Field(gt=0, le=1, max_digits=6, decimal_places=4)
    threshold: Decimal = Field(gt=0, le=1, max_digits=6, decimal_places=4)
    lag_days: int = Field(ge=0, le=90)
    rounding: Rounding
    is_cumulative: bool
    page: int = Field(ge=1)
    quote: str | None = Field(default=None, max_length=2000)


class FuelClauseRead(Schema):
    id: uuid.UUID
    contract_id: uuid.UUID
    instrument_id: uuid.UUID
    fuel_type: str
    base_price: Decimal
    base_on: date
    share: Decimal
    threshold: Decimal
    lag_days: int
    rounding: Rounding
    is_cumulative: bool
    page: int
    quote: str | None
    created_at: datetime


class ContractPricing(Schema):
    tables: list[PriceTableRead]
    fuel_clauses: list[FuelClauseRead]


class FuelPriceWrite(Schema):
    fuel_type: str = Field(min_length=1, max_length=100)
    effective_on: date
    price: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    source: str | None = Field(default=None, max_length=500)


class FuelPriceRead(Schema):
    id: uuid.UUID
    fuel_type: str
    effective_on: date
    price: Decimal
    source: str | None
    created_at: datetime
    created_by_id: uuid.UUID | None = Field(exclude=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_official(self) -> bool:
        """Synced from Petrolimex: read-only, it is the source of record."""
        return self.created_by_id is None


class FuelPriceSyncReport(Schema):
    added: int
    updated: int
    unchanged: int


class FuelPriceFilter(PageParams):
    fuel_type: str | None = Field(default=None, max_length=100)


class FuelAdjustmentParams(Schema):
    on: date


class FuelProposalRead(Schema):
    fuel_on: date
    fuel_price: Decimal
    reference_price: Decimal
    change: Decimal
    factor: Decimal
    effective_on: date


class AdjustedLine(Schema):
    line: PriceLineRead
    proposed_price: Decimal


class FuelAdjustment(Schema):
    """A proposal only: the new prices bind once both parties sign the addendum."""

    clause: FuelClauseRead | None
    proposal: FuelProposalRead | None
    lines: list[AdjustedLine]
