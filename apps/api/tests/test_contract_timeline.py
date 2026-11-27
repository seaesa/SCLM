"""Status on a date comes only from entered facts; a missing date never becomes a guess."""

from dataclasses import replace
from datetime import date

from app.modules.contracts.timeline import Addendum, ContractStatus, Timeline, add_months

_FIXED = Timeline(
    is_settled=True,
    effective_from=date(2022, 3, 15),
    expires_on=date(2023, 3, 14),
    renewal="none",
)


def test_status_follows_the_printed_dates() -> None:
    assert _FIXED.status_on(date(2022, 1, 1)) == ContractStatus.NOT_YET_EFFECTIVE
    assert _FIXED.status_on(date(2023, 3, 14)) == ContractStatus.ACTIVE
    assert _FIXED.status_on(date(2023, 3, 15)) == ContractStatus.EXPIRED


def test_a_contract_is_a_draft_until_settled_and_undetermined_without_a_date() -> None:
    assert replace(_FIXED, is_settled=False).status_on(date(2022, 6, 1)) == ContractStatus.DRAFT
    assert replace(_FIXED, effective_from=None).status_on(date(2022, 6, 1)) == (
        ContractStatus.UNDETERMINED
    )


def test_a_re_signed_contract_ends_the_day_before_its_successor() -> None:
    replaced = replace(_FIXED, replaced_on=date(2022, 9, 1))
    assert replaced.status_on(date(2022, 8, 31)) == ContractStatus.ACTIVE
    assert replaced.status_on(date(2022, 9, 1)) == ContractStatus.REPLACED
    assert replaced.end_on(date(2022, 9, 1)) == date(2022, 8, 31)


def test_an_extension_counts_only_from_its_effective_date() -> None:
    extended = replace(_FIXED, addenda=(Addendum(date(2023, 3, 1), date(2025, 6, 30)),))
    assert extended.end_on(date(2023, 2, 28)) == date(2023, 3, 14)
    assert extended.end_on(date(2024, 1, 1)) == date(2025, 6, 30)
    assert extended.status_on(date(2025, 7, 1)) == ContractStatus.EXPIRED


def test_an_addendum_without_a_new_end_date_changes_nothing() -> None:
    price_only = replace(_FIXED, addenda=(Addendum(date(2023, 1, 1), None),))
    assert price_only.end_on(date(2023, 6, 1)) == date(2023, 3, 14)


def test_without_an_end_date_a_contract_runs_until_it_is_terminated() -> None:
    open_ended = replace(_FIXED, expires_on=None)
    assert open_ended.status_on(date(2030, 1, 1)) == ContractStatus.ACTIVE
    assert open_ended.end_on(date(2030, 1, 1)) is None
    assert add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)


def test_automatic_renewal_moves_the_end_date_one_cycle_at_a_time() -> None:
    renews = replace(_FIXED, renewal="automatic", renewal_months=12)
    assert renews.status_on(date(2023, 3, 15)) == ContractStatus.AUTO_RENEWED
    assert renews.end_on(date(2023, 3, 15)) == date(2024, 3, 14)
    assert renews.end_on(date(2024, 3, 15)) == date(2025, 3, 14)
    unknown_cycle = replace(renews, renewal_months=None)
    assert unknown_cycle.end_on(date(2023, 3, 15)) is None


def test_termination_wins_over_the_end_date() -> None:
    terminated = replace(
        _FIXED, expires_on=date(2025, 6, 30), has_termination=True, terminated_on=date(2025, 3, 25)
    )
    assert terminated.status_on(date(2025, 3, 25)) == ContractStatus.TERMINATED
    assert terminated.end_on(date(2025, 4, 1)) == date(2025, 3, 25)


def test_conditional_renewal_and_undated_termination_need_a_person() -> None:
    conditional = replace(_FIXED, renewal="conditional")
    assert conditional.status_on(date(2023, 3, 1)) == ContractStatus.ACTIVE
    assert conditional.status_on(date(2024, 1, 1)) == ContractStatus.UNDETERMINED
    undated = replace(_FIXED, has_termination=True)
    assert undated.status_on(date(2022, 6, 1)) == ContractStatus.UNDETERMINED
