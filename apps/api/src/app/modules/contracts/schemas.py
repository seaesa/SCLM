import uuid
from datetime import date, datetime
from enum import StrEnum

from pydantic import Field

from app.modules.contracts.fields import (
    Adjustment,
    FieldChoice,
    FieldKey,
    FieldType,
    PaymentFrom,
    Renewal,
)
from app.modules.contracts.models import (
    ContractCategory,
    EventKind,
    InstrumentKind,
    ReviewState,
    SigningState,
    Standing,
)
from app.modules.contracts.timeline import ContractStatus, Lifecycle
from app.modules.partners.schemas import OwnerSummary, PartnerRole, PartnerSummary
from app.shared.pagination import PageParams
from app.shared.schemas import Schema


class FieldSpecRead(Schema):
    key: FieldKey
    type: FieldType
    instrument: InstrumentKind
    is_key: bool
    choices: list[FieldChoice]


class ContractCreate(Schema):
    category: ContractCategory
    # Its files go to a new dossier of this partner.
    partner_id: uuid.UUID
    # Needed for a warehouse lease only (Spider leases from a supplier or to a customer); a
    # customer contract is on the customer side and a contractor contract on the supplier side.
    side: PartnerRole | None = None
    # A draft for the director's approval rather than a signed copy.
    needs_approval: bool = False
    # Set when this contract re-signs an earlier one, which then ends the day before this one
    # takes effect.
    replaces_id: uuid.UUID | None = None


class MissingFact(Schema):
    """A key fact one document of the contract does not have yet."""

    code: str | None
    kind: InstrumentKind
    key: FieldKey


class ContractRead(Schema):
    id: uuid.UUID
    code: str | None
    category: ContractCategory
    partner_id: uuid.UUID
    partner: PartnerSummary
    # The accountant who looks after the partner.
    owner: OwnerSummary | None
    side: PartnerRole
    dossier_id: uuid.UUID
    # Approval of the contract document itself; null when it needs none.
    review_state: ReviewState | None
    # A re-signed contract: the newer one that took its place, from `replaced_on`.
    replaced_by_id: uuid.UUID | None
    replaced_on: date | None
    # As printed on the contract, once entered.
    number: str | None
    signed_on: date | None
    effective_from: date | None
    status: ContractStatus
    lifecycle: Lifecycle
    end_on: date | None
    renewal: Renewal | None
    renewal_notice_days: int | None
    # Last day to give notice of not renewing: end date minus the notice days.
    notice_on: date | None
    # The one decision a running contract needs next, and its date: the notice deadline when it
    # renews by itself, the end date otherwise. Null when nothing is due.
    # Decimal VND as text, e.g. "1250000000"; null when billed on actual volume.
    value_amount: str | None
    # The credit terms in force: the contract's, as changed by addenda since.
    payment_days: int | None
    # Counted in working days rather than calendar days.
    payment_business_days: bool | None
    payment_from: PaymentFrom | None
    # "month_end", or the day of the month as text ("25").
    statement_cutoff: str | None
    addendum_count: int
    # Key facts not recorded yet, over the contract and all its documents.
    missing_count: int
    missing_facts: list[MissingFact]
    is_imported: bool
    created_at: datetime


class RenewalFilter(StrEnum):
    # Has an automatic renewal clause, whether or not it has been used yet.
    AUTOMATIC = "automatic"
    # Past its printed end date and still running on that clause.
    IN_CYCLE = "in_cycle"
    CONDITIONAL = "conditional"
    # No renewal clause, or none recorded.
    NONE = "none"


class PaymentFilter(StrEnum):
    # Up to 15 days of credit, 16 to 30, 31 to 45, over 45, or none recorded.
    UP_TO_15 = "up_to_15"
    UP_TO_30 = "up_to_30"
    UP_TO_45 = "up_to_45"
    OVER_45 = "over_45"
    NONE = "none"


class StatementFilter(StrEnum):
    MONTH_END = "month_end"
    DAY_OF_MONTH = "day_of_month"
    NONE = "none"


class ContractRef(Schema):
    id: uuid.UUID
    code: str | None
    effective_from: date | None
    end_on: date | None


class ContractSort(StrEnum):
    NEWEST = "newest"
    END_ON = "end_on"
    NOTICE_ON = "notice_on"
    CODE = "code"


class ContractFilter(PageParams):
    # Code, printed number or partner name.
    q: str | None = Field(default=None, min_length=2, max_length=100)
    # Any of these; none given means every category.
    categories: list[ContractCategory] | None = None
    lifecycle: Lifecycle | None = None
    partner_id: uuid.UUID | None = None
    dossier_id: uuid.UUID | None = None
    signed_from: date | None = None
    signed_to: date | None = None
    end_from: date | None = None
    end_to: date | None = None
    notice_from: date | None = None
    notice_to: date | None = None
    renewal: RenewalFilter | None = None
    # Any of these credit-term bands and statement cutoffs.
    payments: list[PaymentFilter] | None = None
    statements: list[StatementFilter] | None = None
    # Has a document waiting for a decision.
    is_awaiting_approval: bool | None = None
    # Some document is approved (or needs no approval) but not yet signed by both parties.
    is_awaiting_signature: bool | None = None
    # A key fact is not recorded on some document, or the status cannot be determined.
    is_incomplete: bool | None = None
    # Contracts of the partners this accountant looks after.
    owner_id: uuid.UUID | None = None
    # Contracts of partners nobody looks after yet.
    is_unassigned: bool | None = None
    sort: ContractSort = ContractSort.NEWEST


class ReviewSubmit(Schema):
    # A new version of the draft, uploaded to the dossier; omit to send the current one.
    file_id: uuid.UUID | None = None
    comment: str | None = Field(default=None, max_length=2000)


class SigningWrite(Schema):
    state: SigningState
    # The signed scan, required to mark a reviewed draft as signed by both parties.
    file_id: uuid.UUID | None = None


class ReviewDecision(Schema):
    # Required to reject, so the drafter knows what to change.
    comment: str | None = Field(default=None, max_length=2000)


class FactChange(Schema):
    key: FieldKey
    before: str | None
    after: str | None


class ContractEventRead(Schema):
    id: uuid.UUID
    kind: EventKind
    instrument_id: uuid.UUID | None
    instrument_code: str | None
    changes: list[FactChange]
    signing_state: SigningState | None
    file_id: uuid.UUID | None
    comment: str | None
    actor_id: uuid.UUID
    actor_name: str | None
    created_at: datetime


class InstrumentCreate(Schema):
    kind: InstrumentKind
    file_id: uuid.UUID
    # Spider drafted it: it is approved, then signed, before it counts.
    needs_approval: bool = False


class FactsWrite(Schema):
    # Field key -> ISO date, digits, a choice code (or several, comma-separated); empty clears it.
    values: dict[str, str | None] = Field(max_length=40)


class FieldValueRead(Schema):
    id: uuid.UUID
    key: FieldKey
    value: str | None
    entered_by_id: uuid.UUID
    created_at: datetime


class InstrumentWorkflow(StrEnum):
    AWAITING_APPROVAL = "awaiting_approval"
    # Approved (or needing no approval) but not yet signed by both parties.
    AWAITING_SIGNATURE = "awaiting_signature"


class InstrumentFilter(PageParams):
    # Document code, printed number or partner.
    q: str | None = Field(default=None, min_length=2, max_length=100)
    contract_id: uuid.UUID | None = None
    # Without it: every addendum, schedule and termination (not the contract documents).
    kind: InstrumentKind | None = None
    workflow: InstrumentWorkflow | None = None
    adjustment: Adjustment | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    owner_id: uuid.UUID | None = None
    is_unassigned: bool | None = None
    standing: Standing | None = None
    # A key fact is still missing.
    is_incomplete: bool | None = None


class InstrumentListItem(Schema):
    """One addendum, schedule or termination in the list grouped by contract."""

    id: uuid.UUID
    kind: InstrumentKind
    code: str | None
    number: str | None
    signed_on: date | None
    effective_from: date | None
    effective_to: date | None
    adjustments: list[Adjustment]
    summary: str | None
    review_state: ReviewState | None
    signing_state: SigningState
    standing: Standing | None
    replaced_by_code: str | None
    missing_count: int
    file_id: uuid.UUID
    contract_id: uuid.UUID
    contract_code: str | None
    contract_status: ContractStatus
    # Addenda and schedules of the contract, whatever the filters.
    contract_annex_count: int
    partner: PartnerSummary
    owner: OwnerSummary | None


class InstrumentRead(Schema):
    id: uuid.UUID
    kind: InstrumentKind
    code: str | None
    number: str | None
    signed_on: date | None
    effective_from: date | None
    effective_to: date | None
    adjustments: list[Adjustment]
    summary: str | None
    review_state: ReviewState | None
    signing_state: SigningState
    # Who sent it for approval and who approved it, from the history.
    proposed_by_name: str | None
    approved_by_name: str | None
    # Approved (or needs no approval) and signed by both parties: it changes the contract.
    is_settled: bool
    # Settled addenda and schedules only.
    standing: Standing | None
    # The document that superseded or revoked it.
    replaced_by_code: str | None
    file_id: uuid.UUID
    values: list[FieldValueRead]
    # Key facts that have no value yet.
    missing: list[str]
    # Never sent for approval: a mistake can be removed.
    can_delete: bool


class ApplyingDocument(Schema):
    """The document behind today's prices, fuel base or end date."""

    kind: Adjustment
    instrument_id: uuid.UUID
    code: str | None
    effective_from: date | None


class InstrumentScope(Schema):
    """What another module needs to know about a document before attaching data to it."""

    id: uuid.UUID
    contract_id: uuid.UUID
    side: PartnerRole


class ContractDetail(ContractRead):
    instruments: list[InstrumentRead]
    events: list[ContractEventRead]
    # Recorded here by mistake and nothing of it sent for approval: it can go.
    can_delete: bool
    applying: list[ApplyingDocument]
    # The contract this one re-signs, when recorded that way.
    replaces: ContractRef | None
    # The contract that re-signed this one.
    replaced_by: ContractRef | None
    # Other contracts in force with the same partner and category over the same time: usually
    # a re-signing that was not recorded as one.
    overlapping: list[ContractRef]


class StatusCount(Schema):
    status: ContractStatus
    count: int


class ContractOverview(Schema):
    by_status: list[StatusCount]
    # Documents (contracts and addenda) waiting for an approver.
    awaiting_approval: int
    # Approved documents not yet signed by both parties.
    awaiting_signature: int
    # In force and ending, or due for notice, within DUE_WINDOW_DAYS.
    expiring_soon: int
    notice_soon: int


class ArchivedDocument(Schema):
    """A signed document of the archive seed, named by the SHA-256 of its file."""

    kind: InstrumentKind
    sha256: str
    # Field key -> value as the contract fields accept it (see fields.py).
    facts: dict[str, str] = Field(default_factory=dict)


class ArchivedContract(Schema):
    category: ContractCategory
    document: ArchivedDocument
    annexes: list[ArchivedDocument] = Field(default_factory=list)
    # The main file of the contract this one re-signed, if any.
    replaces: str | None = None


class ArchivedImport(Schema):
    contract_id: uuid.UUID
    is_new: bool
    documents_added: int
    # Facts the fields refused: "<sha256 prefix> <key>=<value>".
    rejected_facts: list[str]
