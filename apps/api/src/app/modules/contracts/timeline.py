"""Contract status on a date, computed from entered readings only. Pure, so it is unit-tested."""

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum

from app.modules.contracts.fields import Renewal


class ContractStatus(StrEnum):
    # Not in force yet: a draft being approved and signed, or the start date not entered.
    DRAFT = "draft"
    # Needs a person's decision: a conditional renewal after the end date, or a termination
    # without its date.
    UNDETERMINED = "undetermined"
    NOT_YET_EFFECTIVE = "not_yet_effective"
    ACTIVE = "active"
    # Past the printed end date with an automatic renewal clause, in renewal cycle `end_on`.
    AUTO_RENEWED = "auto_renewed"
    EXPIRED = "expired"
    # Re-signed: a newer contract with the partner took its place from `replaced_on`.
    REPLACED = "replaced"
    TERMINATED = "terminated"


class Lifecycle(StrEnum):
    """The stages people filter by; each groups one or more statuses."""

    DRAFT = "draft"
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    # Needs a person: a conditional renewal is due, or a termination has no date.
    UNDETERMINED = "undetermined"


LIFECYCLE_STATUSES: dict[Lifecycle, tuple[ContractStatus, ...]] = {
    Lifecycle.DRAFT: (ContractStatus.DRAFT,),
    Lifecycle.ACTIVE: (
        ContractStatus.ACTIVE,
        ContractStatus.AUTO_RENEWED,
        ContractStatus.NOT_YET_EFFECTIVE,
    ),
    Lifecycle.EXPIRED: (ContractStatus.EXPIRED, ContractStatus.REPLACED),
    Lifecycle.TERMINATED: (ContractStatus.TERMINATED,),
    Lifecycle.UNDETERMINED: (ContractStatus.UNDETERMINED,),
}

LIFECYCLE_OF: dict[ContractStatus, Lifecycle] = {
    status: lifecycle for lifecycle, statuses in LIFECYCLE_STATUSES.items() for status in statuses
}


def add_months(start: date, months: int) -> date:
    """Same day `months` later, clamped to the month's last day (31 Jan + 1 month = 28/29 Feb)."""
    index = start.month - 1 + months
    year, month = start.year + index // 12, index % 12 + 1
    return date(year, month, min(start.day, calendar.monthrange(year, month)[1]))


@dataclass(frozen=True)
class Addendum:
    effective_from: date | None
    extends_to: date | None


@dataclass(frozen=True)
class Timeline:
    # The contract document is approved (if it needed approval) and signed by both parties.
    is_settled: bool
    effective_from: date | None
    # Empty: no end date, so the contract runs until it is terminated or replaced.
    expires_on: date | None = None
    renewal: str | None = None
    renewal_months: int | None = None
    addenda: tuple[Addendum, ...] = ()
    terminated_on: date | None = None
    has_termination: bool = False
    # The day the contract that replaced it took effect.
    replaced_on: date | None = None

    def _printed_end(self, on: date) -> date | None:
        """End date in force on `on`: from the addendum that took effect last among those already
        effective and extending the term (on a tie, the one recorded last), else the contract's."""
        extending = [
            a for a in self.addenda if a.extends_to and a.effective_from and a.effective_from <= on
        ]
        if extending:
            return sorted(extending, key=lambda a: a.effective_from or on)[-1].extends_to
        return self.expires_on

    def end_on(self, on: date) -> date | None:
        """The end date that matters on `on`; for an auto-renewed contract, its current cycle's."""
        if self.terminated_on is not None and self.terminated_on <= on:
            return self.terminated_on
        if self.replaced_on is not None and self.replaced_on <= on:
            return self.replaced_on - timedelta(days=1)
        end = self._printed_end(on)
        if end is None or on <= end or self.renewal != Renewal.AUTOMATIC:
            return end
        if not self.renewal_months:
            return None
        cycle = 1
        while (cycle_end := add_months(end + timedelta(days=1), self.renewal_months * cycle)) <= on:
            cycle += 1
        return cycle_end - timedelta(days=1)

    def status_on(self, on: date) -> ContractStatus:
        if not self.is_settled:
            return ContractStatus.DRAFT
        if self.effective_from is None:
            # Signed, but neither a start nor a signing date is known yet.
            return ContractStatus.UNDETERMINED
        if self.has_termination:
            if self.terminated_on is None:
                return ContractStatus.UNDETERMINED
            if self.terminated_on <= on:
                return ContractStatus.TERMINATED
        if self.replaced_on is not None and self.replaced_on <= on:
            return ContractStatus.REPLACED
        if on < self.effective_from:
            return ContractStatus.NOT_YET_EFFECTIVE
        end = self._printed_end(on)
        if end is None:
            return ContractStatus.ACTIVE
        if on <= end:
            return ContractStatus.ACTIVE
        match self.renewal:
            case Renewal.AUTOMATIC:
                return ContractStatus.AUTO_RENEWED
            case Renewal.CONDITIONAL:
                return ContractStatus.UNDETERMINED
            case _:
                return ContractStatus.EXPIRED
