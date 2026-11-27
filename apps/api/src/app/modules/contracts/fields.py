"""Which facts each instrument must carry, and how a reading is normalized. The backend owns this
list; clients render the form from `GET /contract-fields`."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Literal, get_args

from app.modules.contracts.models import InstrumentKind


class FieldType(StrEnum):
    TEXT = "text"
    DATE = "date"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    CHOICE = "choice"
    # Several codes from `choices`, stored comma-separated in the order of `choices`.
    CHOICES = "choices"
    # A sum of money in VND: digits with up to two decimals, stored as plain text.
    AMOUNT = "amount"


class Renewal(StrEnum):
    NONE = "none"
    AUTOMATIC = "automatic"
    # "May be renewed" or renewal subject to a condition: only a person can say it happened.
    CONDITIONAL = "conditional"


class PaymentFrom(StrEnum):
    """What the credit term is counted from."""

    INVOICE = "invoice"
    # The day the statement is closed or agreed by both sides.
    STATEMENT = "statement"
    # The day the goods are delivered or the service is done.
    DELIVERY = "delivery"
    OTHER = "other"


# When the statement of the period is closed: the last day of the month or a set day. A
# cutoff by shipment or by week has no date to keep, so it is left empty.
MONTH_END = "month_end"
StatementCutoff = Literal[
    "month_end",
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14",
    "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28",
]  # fmt: skip
STATEMENT_CUTOFFS: tuple[str, ...] = get_args(StatementCutoff)


class FieldKey(StrEnum):
    """Every fact a document can carry; clients label each one, so the list is part of the API."""

    NUMBER = "number"
    SIGNED_ON = "signed_on"
    EFFECTIVE_FROM = "effective_from"
    EFFECTIVE_TO = "effective_to"
    EXPIRES_ON = "expires_on"
    RENEWAL = "renewal"
    RENEWAL_MONTHS = "renewal_months"
    RENEWAL_NOTICE_DAYS = "renewal_notice_days"
    VALUE_AMOUNT = "value_amount"
    PAYMENT_DAYS = "payment_days"
    PAYMENT_BUSINESS_DAYS = "payment_business_days"
    PAYMENT_FROM = "payment_from"
    STATEMENT_CUTOFF = "statement_cutoff"
    SUMMARY = "summary"
    REPLACES = "replaces"
    ADJUSTMENTS = "adjustments"
    EXTENDS_TO = "extends_to"
    REVOKES = "revokes"
    TERMINATED_ON = "terminated_on"


class Adjustment(StrEnum):
    """What an addendum changes."""

    PRICE = "price"
    ROUTE = "route"
    FUEL = "fuel"
    PAYMENT = "payment"
    TERM = "term"
    OTHER = "other"
    # Annuls an earlier addendum, named in `revokes`.
    REVOKE = "revoke"


# A value a choice field can hold; clients label each one, so the set is part of the API.
type FieldChoice = Renewal | PaymentFrom | Adjustment | StatementCutoff


# Changes a later document replaces outright: one fuel base and one end date at a time.
# Prices and routes add up (a new table often adds a route), so a price document is only
# replaced when a later one says so in `replaces`.
REPLACING = frozenset({Adjustment.FUEL, Adjustment.TERM})


@dataclass(frozen=True)
class FieldSpec:
    key: str
    type: FieldType
    instrument: InstrumentKind
    # A fact the system needs to tell where the document stands: reported as missing until it
    # is recorded, unless another fact stands in for it (`DEFAULTS_FROM`).
    is_key: bool
    choices: tuple[str, ...] = field(default=())

    def __post_init__(self) -> None:
        # A fact clients cannot label must not reach them: every key is a `FieldKey`.
        FieldKey(self.key)


_C, _S = InstrumentKind.CONTRACT, InstrumentKind.SCHEDULE
_A, _T = InstrumentKind.ADDENDUM, InstrumentKind.TERMINATION

# Only what is needed to manage, filter and remind; the signed paper remains the reference.
# Key facts are those the contract list reports as missing when nobody has recorded them.
FIELDS: tuple[FieldSpec, ...] = (
    FieldSpec("number", FieldType.TEXT, _C, False),
    FieldSpec("signed_on", FieldType.DATE, _C, False),
    # Defaults to the signing date (Civil Code 2015, art. 401): missing only without both.
    FieldSpec("effective_from", FieldType.DATE, _C, True),
    # Empty means the contract has no end date: it runs until it is terminated or replaced.
    FieldSpec("expires_on", FieldType.DATE, _C, False),
    FieldSpec("renewal", FieldType.CHOICE, _C, False, tuple(Renewal)),
    FieldSpec("renewal_months", FieldType.INTEGER, _C, False),
    FieldSpec("renewal_notice_days", FieldType.INTEGER, _C, False),
    # Empty when billed on actual volume.
    FieldSpec("value_amount", FieldType.AMOUNT, _C, False),
    # Days of credit: 15, 30, 45, 60...
    FieldSpec("payment_days", FieldType.INTEGER, _C, False),
    FieldSpec("payment_business_days", FieldType.BOOLEAN, _C, False),
    FieldSpec("payment_from", FieldType.CHOICE, _C, False, tuple(PaymentFrom)),
    FieldSpec("statement_cutoff", FieldType.CHOICE, _C, False, STATEMENT_CUTOFFS),
    FieldSpec("number", FieldType.TEXT, _S, False),
    # Defaults to the contract's start: a table signed with the contract applies from day one.
    FieldSpec("effective_from", FieldType.DATE, _S, False),
    FieldSpec("summary", FieldType.TEXT, _S, False),
    # Codes of earlier annexes this one replaces, comma separated.
    FieldSpec("replaces", FieldType.TEXT, _S, False),
    FieldSpec("number", FieldType.TEXT, _A, False),
    FieldSpec("signed_on", FieldType.DATE, _A, False),
    # Defaults to the signing date: missing only without both.
    FieldSpec("effective_from", FieldType.DATE, _A, True),
    # The addendum's own end, when it says it applies only until a date.
    FieldSpec("effective_to", FieldType.DATE, _A, False),
    FieldSpec("adjustments", FieldType.CHOICES, _A, True, tuple(Adjustment)),
    FieldSpec("summary", FieldType.TEXT, _A, False),
    # Only when the contract's term is extended; a price table extension leaves it empty.
    FieldSpec("extends_to", FieldType.DATE, _A, False),
    FieldSpec("payment_days", FieldType.INTEGER, _A, False),
    FieldSpec("payment_business_days", FieldType.BOOLEAN, _A, False),
    FieldSpec("payment_from", FieldType.CHOICE, _A, False, tuple(PaymentFrom)),
    FieldSpec("statement_cutoff", FieldType.CHOICE, _A, False, STATEMENT_CUTOFFS),
    FieldSpec("replaces", FieldType.TEXT, _A, False),
    # The code of the addendum this one annuls.
    FieldSpec("revokes", FieldType.TEXT, _A, False),
    FieldSpec("number", FieldType.TEXT, _T, False),
    FieldSpec("signed_on", FieldType.DATE, _T, False),
    FieldSpec("terminated_on", FieldType.DATE, _T, True),
)

# A key fact another one stands in for when it is empty.
DEFAULTS_FROM = {
    # Civil Code 2015, art. 401: a contract takes effect when signed unless it says otherwise.
    "effective_from": "signed_on",
    # A termination takes effect when signed unless it names another day.
    "terminated_on": "signed_on",
}

SPECS: dict[tuple[InstrumentKind, str], FieldSpec] = {(s.instrument, s.key): s for s in FIELDS}


class InvalidValueError(ValueError):
    pass


def normalize(spec: FieldSpec, raw: str) -> str:
    """Return the stored text for a typed value, or raise `InvalidValueError`."""
    raw = raw.strip()
    match spec.type:
        case FieldType.TEXT:
            if not raw:
                raise InvalidValueError
            return raw
        case FieldType.DATE:
            try:
                return date.fromisoformat(raw).isoformat()
            except ValueError as exc:
                raise InvalidValueError from exc
        case FieldType.INTEGER:
            if not raw.isdigit():
                raise InvalidValueError
            return str(int(raw))
        case FieldType.BOOLEAN:
            if raw not in ("true", "false"):
                raise InvalidValueError
            return raw
        case FieldType.CHOICE:
            if raw not in spec.choices:
                raise InvalidValueError
            return raw
        case FieldType.CHOICES:
            picked = {code.strip() for code in raw.split(",") if code.strip()}
            if not picked or not picked <= set(spec.choices):
                raise InvalidValueError
            return ",".join(c for c in spec.choices if c in picked)
        case FieldType.AMOUNT:
            return _amount(raw)


def _amount(raw: str) -> str:
    if not raw or raw.startswith(("+", "-")):
        raise InvalidValueError
    try:
        amount = Decimal(raw)
    except InvalidOperation as exc:
        raise InvalidValueError from exc
    exponent = amount.as_tuple().exponent
    if not amount.is_finite() or (isinstance(exponent, int) and exponent < -2):
        raise InvalidValueError
    return format(amount.normalize(), "f")


# The credit terms: an addendum that changes the payment may restate any of them, and the
# latest one in force wins key by key over the contract.
PAYMENT_KEYS = (
    "payment_days",
    "payment_business_days",
    "payment_from",
    "statement_cutoff",
)


def key_fields(kind: InstrumentKind) -> list[str]:
    return [s.key for s in FIELDS if s.instrument == kind and s.is_key]
