"""Pure pricing rules: which price line governs an order on a date, and what a fuel clause
proposes once the fuel price moves. Nothing here guesses: a lapsed table is reported as lapsed,
never silently replaced by an older one."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from enum import StrEnum


class TableMode(StrEnum):
    # The table replaces every earlier line of the contract.
    REPLACE = "replace"
    # The table changes only the lines it lists; the others stay as they were.
    AMEND = "amend"


class Rounding(StrEnum):
    NONE = "none"
    DOWN_100 = "down_100"
    NEAREST_100 = "nearest_100"
    DOWN_1000 = "down_1000"
    NEAREST_1000 = "nearest_1000"


_STEPS = {
    Rounding.DOWN_100: (Decimal(100), ROUND_DOWN),
    Rounding.NEAREST_100: (Decimal(100), ROUND_HALF_UP),
    Rounding.DOWN_1000: (Decimal(1000), ROUND_DOWN),
    Rounding.NEAREST_1000: (Decimal(1000), ROUND_HALF_UP),
}


def round_price(value: Decimal, rounding: Rounding) -> Decimal:
    if rounding == Rounding.NONE:
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    step, mode = _STEPS[rounding]
    return (value / step).quantize(Decimal(1), rounding=mode) * step


type PriceKey = tuple[str, str, str, str, str]


def _norm(text: str | None) -> str:
    return " ".join((text or "").split()).casefold()


def price_key(
    service: str, origin: str | None, destination: str | None, vehicle: str | None, unit: str
) -> PriceKey:
    """Two lines are the same price when these match, ignoring case and spacing."""
    return (_norm(service), _norm(origin), _norm(destination), _norm(vehicle), _norm(unit))


@dataclass(frozen=True)
class Table[LineT]:
    effective_from: date
    effective_to: date | None
    mode: TableMode
    created_at: datetime
    lines: Sequence[tuple[PriceKey, LineT]]


@dataclass(frozen=True)
class Governing[LineT]:
    line: LineT
    table: "Table[LineT]"
    # The table that set this price ended before the date and nothing replaced it.
    is_lapsed: bool


def governing_lines[LineT](tables: Sequence[Table[LineT]], on: date) -> list[Governing[LineT]]:
    """Applies the tables in force by `on` in date order (recording order breaks ties)."""
    state: dict[PriceKey, tuple[LineT, Table[LineT]]] = {}
    started = sorted(
        (t for t in tables if t.effective_from <= on),
        key=lambda t: (t.effective_from, t.created_at),
    )
    for table in started:
        if table.mode == TableMode.REPLACE:
            state = {}
        for key, line in table.lines:
            state[key] = (line, table)
    return [
        Governing(line, table, table.effective_to is not None and table.effective_to < on)
        for line, table in state.values()
    ]


def previous_lines[LineT](
    tables: Sequence[Table[LineT]], table: Table[LineT]
) -> dict[PriceKey, LineT]:
    """The price each key had just before `table` started: what an addendum changed from."""
    earlier = [
        t
        for t in tables
        if (t.effective_from, t.created_at) < (table.effective_from, table.created_at)
    ]
    # Lapsed or not, the last agreed price is what the parties compare against.
    state: dict[PriceKey, LineT] = {}
    for t in sorted(earlier, key=lambda t: (t.effective_from, t.created_at)):
        if t.mode == TableMode.REPLACE:
            state = {}
        state.update(t.lines)
    return state


def price_change(previous: Decimal, new: Decimal) -> Decimal | None:
    """Fractional change (0.05 = +5%), to 4 places; none when there was no price to compare."""
    if previous == 0:
        return None
    return (new / previous - 1).quantize(Decimal("0.0001"))


@dataclass(frozen=True)
class FuelClause:
    base_price: Decimal
    base_on: date
    # Share of the transport price that follows fuel (D), e.g. 0.35.
    share: Decimal
    # Change that triggers an adjustment, e.g. 0.10 for ±10%.
    threshold: Decimal
    # New prices apply this many days after the fuel price date.
    lag_days: int
    rounding: Rounding
    # Measured against the base price; otherwise against the previous fuel price.
    is_cumulative: bool


@dataclass(frozen=True)
class FuelProposal:
    fuel_on: date
    fuel_price: Decimal
    reference_price: Decimal
    change: Decimal
    factor: Decimal
    effective_on: date

    def adjust(self, unit_price: Decimal, rounding: Rounding) -> Decimal:
        return round_price(unit_price * self.factor, rounding)


def propose(
    clause: FuelClause, prices: Sequence[tuple[date, Decimal]], on: date
) -> FuelProposal | None:
    """The first fuel price after the base date, up to `on`, that moves past the threshold."""
    reference = clause.base_price
    for fuel_on, price in sorted(p for p in prices if clause.base_on < p[0] <= on):
        change = (price - reference) / reference
        if abs(change) >= clause.threshold:
            return FuelProposal(
                fuel_on=fuel_on,
                fuel_price=price,
                reference_price=reference,
                change=change,
                factor=1 + change * clause.share,
                effective_on=fuel_on + timedelta(days=clause.lag_days),
            )
        if not clause.is_cumulative:
            reference = price
    return None
