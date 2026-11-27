"""Which price governs an order, and what a fuel clause proposes, follow the paper exactly."""
# Price lines are Vietnamese: cspell:ignore chuyển chuyến Bình SASCO tấn

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from app.modules.pricing.rules import (
    FuelClause,
    Rounding,
    Table,
    TableMode,
    governing_lines,
    price_key,
    propose,
    round_price,
)

_ROUTE = price_key("Vận chuyển", "Kho Tân Bình", "SASCO", "Xe 1 tấn", "chuyến")
_OTHER = price_key("Vận chuyển", "Kho Tân Bình", "SASCO", "Xe 2 tấn", "chuyến")


def _table(
    start: date, mode: TableMode, *lines: tuple[tuple[str, ...], str], end: date | None = None
) -> Table[str]:
    return Table(start, end, mode, datetime.now(UTC), lines)  # type: ignore[arg-type]


def test_masan_fuel_clause_reproduces_the_signed_price() -> None:
    clause = FuelClause(
        base_price=Decimal(23320),
        base_on=date(2023, 7, 1),
        share=Decimal("0.35"),
        threshold=Decimal("0.10"),
        lag_days=10,
        rounding=Rounding.DOWN_100,
        is_cumulative=True,
    )
    prices = [(date(2023, 7, 11), Decimal(24500)), (date(2023, 7, 23), Decimal(25760))]
    proposal = propose(clause, prices, date(2023, 8, 31))
    assert proposal is not None
    assert proposal.fuel_on == date(2023, 7, 23)
    assert proposal.effective_on == date(2023, 8, 2)
    assert proposal.adjust(Decimal(1525700), Rounding.DOWN_100) == Decimal(1581500)


def test_small_steps_trigger_only_when_the_clause_is_cumulative() -> None:
    steps = [(date(2024, 1, d), Decimal(p)) for d, p in [(5, 21000), (15, 22000), (25, 23000)]]
    terms = {
        "base_price": Decimal(20000),
        "base_on": date(2024, 1, 1),
        "share": Decimal("0.3"),
        "threshold": Decimal("0.10"),
        "lag_days": 0,
        "rounding": Rounding.NONE,
    }
    cumulative = propose(FuelClause(**terms, is_cumulative=True), steps, date(2024, 2, 1))  # type: ignore[arg-type]
    stepwise = propose(FuelClause(**terms, is_cumulative=False), steps, date(2024, 2, 1))  # type: ignore[arg-type]
    assert cumulative is not None
    assert cumulative.fuel_on == date(2024, 1, 15)
    assert stepwise is None


def test_rounding_follows_the_clause() -> None:
    assert round_price(Decimal("1581572.9"), Rounding.DOWN_100) == Decimal(1581500)
    assert round_price(Decimal("1581550"), Rounding.NEAREST_100) == Decimal(1581600)
    assert round_price(Decimal("1581572.9"), Rounding.NONE) == Decimal("1581572.90")


def test_a_replacing_table_drops_lines_it_does_not_repeat() -> None:
    tables = [
        _table(date(2023, 1, 1), TableMode.REPLACE, (_ROUTE, "old 1t"), (_OTHER, "old 2t")),
        _table(date(2023, 6, 1), TableMode.REPLACE, (_ROUTE, "new 1t")),
    ]
    assert [g.line for g in governing_lines(tables, date(2023, 7, 1))] == ["new 1t"]
    assert sorted(g.line for g in governing_lines(tables, date(2023, 5, 31))) == [
        "old 1t",
        "old 2t",
    ]


def test_an_amending_table_changes_only_the_lines_it_lists() -> None:
    tables = [
        _table(date(2023, 1, 1), TableMode.REPLACE, (_ROUTE, "old 1t"), (_OTHER, "old 2t")),
        _table(date(2023, 6, 1), TableMode.AMEND, (_ROUTE, "new 1t")),
    ]
    assert sorted(g.line for g in governing_lines(tables, date(2023, 7, 1))) == [
        "new 1t",
        "old 2t",
    ]


def test_a_lapsed_price_is_flagged_not_replaced_by_an_older_one() -> None:
    tables = [
        _table(date(2023, 1, 1), TableMode.REPLACE, (_ROUTE, "base")),
        _table(date(2023, 4, 1), TableMode.AMEND, (_ROUTE, "promo"), end=date(2023, 5, 13)),
    ]
    [inside] = governing_lines(tables, date(2023, 5, 13))
    [after] = governing_lines(tables, date(2023, 5, 14))
    assert (inside.line, inside.is_lapsed) == ("promo", False)
    assert (after.line, after.is_lapsed) == ("promo", True)


def test_same_day_tables_apply_in_recording_order() -> None:
    first = _table(date(2023, 1, 1), TableMode.AMEND, (_ROUTE, "first"))
    second = Table(
        first.effective_from,
        None,
        TableMode.AMEND,
        first.created_at + timedelta(seconds=1),
        [(_ROUTE, "second")],
    )
    [governing] = governing_lines([second, first], date(2023, 1, 2))
    assert governing.line == "second"


def test_price_keys_ignore_case_and_spacing() -> None:
    assert price_key(" vận  chuyển", "kho tân bình", "sasco", "XE 1 TẤN", "Chuyến") == _ROUTE
