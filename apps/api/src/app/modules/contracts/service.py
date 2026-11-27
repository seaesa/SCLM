import uuid
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.modules.contracts.fields import (
    DEFAULTS_FROM,
    FIELDS,
    PAYMENT_KEYS,
    REPLACING,
    SPECS,
    Adjustment,
    FieldSpec,
    InvalidValueError,
    Renewal,
    key_fields,
    normalize,
)
from app.modules.contracts.models import (
    CODE_PREFIXES,
    Contract,
    ContractCategory,
    ContractEvent,
    EventKind,
    FieldValue,
    Instrument,
    InstrumentKind,
    ReviewState,
    SigningState,
    Standing,
)
from app.modules.contracts.repository import (
    CodeCounterRepository,
    ContractEventRepository,
    ContractRepository,
    FieldValueRepository,
    InstrumentRepository,
)
from app.modules.contracts.schemas import (
    ArchivedContract,
    ArchivedImport,
    ContractCreate,
    ContractDetail,
    ContractEventRead,
    ContractFilter,
    ContractOverview,
    ContractRead,
    ContractRef,
    FactsWrite,
    FieldSpecRead,
    FieldValueRead,
    InstrumentCreate,
    InstrumentFilter,
    InstrumentListItem,
    InstrumentRead,
    InstrumentScope,
    ReviewDecision,
    ReviewSubmit,
    SigningWrite,
    StatusCount,
)
from app.modules.contracts.timeline import (
    LIFECYCLE_OF,
    Addendum,
    ContractStatus,
    Lifecycle,
    Timeline,
)
from app.modules.documents.models import DocumentSide
from app.modules.documents.service import DocumentService
from app.modules.partners.schemas import OwnerSummary, PartnerRole, PartnerSummary
from app.modules.partners.service import PartnerService
from app.modules.users.service import UserService
from app.shared.clock import business_today
from app.shared.schemas import ErrorCode, Page

# Numbered PL01, PL02... under the contract code, in the order they are recorded.
_ANNEXES = (InstrumentKind.ADDENDUM, InstrumentKind.SCHEDULE)
_REFRESH_BATCH = 500


# The side a customer or contractor contract is on; a warehouse lease can be on either.
_SIDE_OF: dict[ContractCategory, PartnerRole] = {
    ContractCategory.CUSTOMER: PartnerRole.CUSTOMER,
    ContractCategory.CONTRACTOR: PartnerRole.SUPPLIER,
}


class _Loaded:
    """A contract with its documents and their current readings, loaded in a few queries."""

    def __init__(
        self,
        contract: Contract,
        instruments: Sequence[Instrument],
        values: dict[uuid.UUID, list[FieldValue]],
        partner: PartnerSummary,
        owner: OwnerSummary | None,
    ) -> None:
        self.contract = contract
        self.instruments = instruments
        self.values = values
        self.partner = partner
        self.owner = owner

    def facts(self, instrument: Instrument) -> dict[str, str | None]:
        return {v.key: v.value for v in self.values.get(instrument.id, []) if v.value is not None}

    def missing(self, instrument: Instrument) -> list[str]:
        """Key facts neither recorded nor standing in from another fact."""
        facts = self.facts(instrument)
        return [
            k
            for k in key_fields(instrument.kind)
            if k not in facts and DEFAULTS_FROM.get(k) not in facts
        ]

    @staticmethod
    def is_settled(instrument: Instrument) -> bool:
        """Approved when it needed approval, and signed by both parties."""
        return (
            instrument.review_state in (None, ReviewState.APPROVED)
            and instrument.signing_state == SigningState.SIGNED
        )

    def _standings(
        self, on: date, status: ContractStatus
    ) -> tuple[dict[uuid.UUID, tuple[Standing, uuid.UUID | None]], dict[str, Instrument]]:
        """Where each settled addendum and schedule stands on `on` and which document
        replaced or annulled it, with the document behind today's fuel base and end date.

        Only the fuel base and the end date are replaced by the next document that sets them.
        Prices, routes and the rest add up while the contract runs: a later document replaces
        them only when it names them in `replaces` (or annuls them in `revokes`)."""
        main = self.main
        main_facts = self.facts(main) if main else {}
        contract_start = _date(main_facts.get("effective_from") or main_facts.get("signed_on"))
        annexes = [i for i in self.instruments if i.kind in _ANNEXES and self.is_settled(i)]
        by_code = {i.code: i for i in annexes if i.code}
        start: dict[uuid.UUID, date | None] = {}
        changes: dict[uuid.UUID, set[str]] = {}
        ended_by: dict[uuid.UUID, tuple[Standing, uuid.UUID]] = {}
        for i in annexes:
            facts = self.facts(i)
            if i.kind == InstrumentKind.SCHEDULE:
                start[i.id] = _date(facts.get("effective_from")) or contract_start
                changes[i.id] = {Adjustment.PRICE}
            else:
                start[i.id] = _date(facts.get("effective_from") or facts.get("signed_on"))
                changes[i.id] = (_codes(facts.get("adjustments")) - {Adjustment.TERM}) | (
                    {Adjustment.TERM} if facts.get("extends_to") else set()
                )
        for i in annexes:
            began = start[i.id]
            if began is not None and began > on:
                continue
            facts = self.facts(i)
            for code in _codes(facts.get("replaces")):
                if (target := by_code.get(code)) and target is not i:
                    ended_by.setdefault(target.id, (Standing.SUPERSEDED, i.id))
            if Adjustment.REVOKE in changes[i.id] and (
                target := by_code.get(facts.get("revokes") or "")
            ):
                ended_by[target.id] = (Standing.REVOKED, i.id)

        def order(i: Instrument) -> tuple[date, datetime]:
            return (start[i.id] or date.min, i.created_at)

        # For each replaced kind, the documents that set it and have begun, oldest first.
        chains = {
            kind: sorted(
                (
                    i
                    for i in annexes
                    if kind in changes[i.id]
                    and i.id not in ended_by
                    and (start[i.id] or date.min) <= on
                ),
                key=order,
            )
            for kind in REPLACING
        }
        is_running = status not in (
            ContractStatus.EXPIRED,
            ContractStatus.REPLACED,
            ContractStatus.TERMINATED,
        )
        result: dict[uuid.UUID, tuple[Standing, uuid.UUID | None]] = {}
        applying: dict[str, Instrument] = {}
        for i in annexes:
            began, end = start[i.id], _date(self.facts(i).get("effective_to"))
            latest_for = [kind for kind, chain in chains.items() if chain and chain[-1] is i]
            if i.id in ended_by:
                result[i.id] = ended_by[i.id]
            elif not is_running or (end is not None and end < on):
                result[i.id] = (Standing.LAPSED, None)
            elif began is not None and began > on:
                result[i.id] = (Standing.PENDING, None)
            elif latest_for:
                result[i.id] = (Standing.APPLYING, None)
                applying.update(dict.fromkeys(latest_for, i))
            elif changes[i.id] and changes[i.id] <= REPLACING:
                successor = min(
                    (
                        chain[chain.index(i) + 1]
                        for chain in chains.values()
                        if i in chain and chain[-1] is not i
                    ),
                    key=order,
                )
                result[i.id] = (Standing.SUPERSEDED, successor.id)
            else:
                result[i.id] = (Standing.IN_FORCE, None)
        return result, applying

    def standings(
        self, on: date, status: ContractStatus
    ) -> dict[uuid.UUID, tuple[Standing, uuid.UUID | None]]:
        return self._standings(on, status)[0]

    def applying(self, on: date, status: ContractStatus) -> dict[str, Instrument]:
        """The document behind today's fuel base and end date."""
        return self._standings(on, status)[1]

    def payment_terms(self, on: date) -> dict[str, str | None]:
        """The credit terms in force on `on`: the contract's, each overridden by the latest
        settled addendum already started that restates it."""
        main = self.main
        terms = {k: (self.facts(main).get(k) if main else None) for k in PAYMENT_KEYS}
        revoked = self.revoked_ids()
        for i in self.in_order():
            if i.kind != InstrumentKind.ADDENDUM or not self.is_settled(i) or i.id in revoked:
                continue
            facts = self.facts(i)
            began = _date(facts.get("effective_from") or facts.get("signed_on"))
            if began is None or began > on:
                continue
            restated = {k: facts[k] for k in PAYMENT_KEYS if facts.get(k)}
            terms.update(restated)
        return terms

    def revoked_ids(self) -> set[uuid.UUID]:
        """Annexes another settled addendum annulled, whatever the date: what was annulled
        never extends the contract."""
        by_code = {i.code: i.id for i in self.instruments if i.code}
        return {
            target
            for i in self.instruments
            if i.kind == InstrumentKind.ADDENDUM
            and self.is_settled(i)
            and Adjustment.REVOKE in _codes(self.facts(i).get("adjustments"))
            and (target := by_code.get(self.facts(i).get("revokes") or ""))
        }

    def in_order(self) -> list[Instrument]:
        """The contract document first, then annexes by the day they start (a schedule with no
        date starts with the contract), terminations last."""
        main = self.main
        main_facts = self.facts(main) if main else {}
        contract_start = _date(main_facts.get("effective_from") or main_facts.get("signed_on"))
        rank = {InstrumentKind.CONTRACT: 0, InstrumentKind.TERMINATION: 2}

        def key(i: Instrument) -> tuple[int, date, datetime]:
            facts = self.facts(i)
            began = _date(
                facts.get("effective_from") or facts.get("signed_on") or facts.get("terminated_on")
            )
            if began is None and i.kind == InstrumentKind.SCHEDULE:
                began = contract_start
            return (rank.get(InstrumentKind(i.kind), 1), began or date.max, i.created_at)

        return sorted(self.instruments, key=key)

    @property
    def main(self) -> Instrument | None:
        return next((i for i in self.instruments if i.kind == InstrumentKind.CONTRACT), None)

    def timeline(self) -> Timeline:
        """Built only from settled documents: an addendum still in draft changes nothing."""
        counted = [i for i in self.instruments if self.is_settled(i)]
        main = self.main if self.main in counted else None
        facts = self.facts(main) if main else {}
        terminations = [self.facts(i) for i in counted if i.kind == InstrumentKind.TERMINATION]
        revoked = self.revoked_ids()
        return Timeline(
            is_settled=main is not None,
            # A contract takes effect when signed unless it says otherwise (Civil Code 2015, art. 401).
            effective_from=_date(facts.get("effective_from") or facts.get("signed_on")),
            expires_on=_date(facts.get("expires_on")),
            renewal=facts.get("renewal"),
            renewal_months=_int(facts.get("renewal_months")) or _term_months(facts),
            addenda=tuple(
                Addendum(
                    effective_from=_date(
                        self.facts(i).get("effective_from") or self.facts(i).get("signed_on")
                    ),
                    extends_to=_date(self.facts(i).get("extends_to")),
                )
                for i in counted
                if i.kind == InstrumentKind.ADDENDUM and i.id not in revoked
            ),
            has_termination=bool(terminations),
            terminated_on=min(
                (
                    d
                    for t in terminations
                    if (d := _date(t.get("terminated_on") or t.get("signed_on")))
                ),
                default=None,
            ),
            replaced_on=self.contract.replaced_on,
        )

    def read(self, on: date) -> ContractRead:
        timeline = self.timeline()
        main = self.main
        facts = self.facts(main) if main else {}
        status = timeline.status_on(on)
        end_on = timeline.end_on(on) if status != ContractStatus.DRAFT else None
        notice_days = _int(facts.get("renewal_notice_days"))
        is_running = status in (ContractStatus.ACTIVE, ContractStatus.AUTO_RENEWED)
        renews = facts.get("renewal") == Renewal.AUTOMATIC
        # The notice stops an automatic renewal, so only a running contract that renews by
        # itself has a deadline to meet.
        notice_on = (
            end_on - timedelta(days=notice_days)
            if end_on and notice_days is not None and renews and is_running
            else None
        )
        return ContractRead.model_validate(
            {
                **{k: getattr(self.contract, k) for k in _CONTRACT_FIELDS},
                "partner": self.partner,
                "owner": self.owner,
                "review_state": main.review_state if main else None,
                "number": facts.get("number"),
                "signed_on": _date(facts.get("signed_on")),
                "effective_from": timeline.effective_from,
                "renewal": facts.get("renewal"),
                "renewal_notice_days": notice_days,
                "notice_on": notice_on,
                "value_amount": facts.get("value_amount"),
                **_payment_read(self.payment_terms(on)),
                "status": status,
                "lifecycle": LIFECYCLE_OF[status],
                "end_on": end_on,
                "addendum_count": sum(1 for i in self.instruments if i.kind in _ANNEXES),
                "missing_count": sum(len(self.missing(i)) for i in self.instruments),
                "missing_facts": [
                    {"code": i.code, "kind": i.kind, "key": key}
                    for i in self.instruments
                    for key in self.missing(i)
                ],
            }
        )


def _payment_read(terms: dict[str, str | None]) -> dict[str, object]:
    return {
        "payment_days": _int(terms["payment_days"]),
        "payment_business_days": (
            None
            if terms["payment_business_days"] is None
            else terms["payment_business_days"] == "true"
        ),
        "payment_from": terms["payment_from"],
        "statement_cutoff": terms["statement_cutoff"],
    }


def _ref(contract: Contract) -> ContractRef:
    return ContractRef(
        id=contract.id,
        code=contract.code,
        effective_from=contract.effective_from,
        end_on=contract.end_on,
    )


_CONTRACT_FIELDS = (
    "id",
    "code",
    "category",
    "partner_id",
    "side",
    "dossier_id",
    "replaced_by_id",
    "replaced_on",
    "is_imported",
    "created_at",
)


_EXPORT_PAGE_SIZE = 100


def _owner(partner: PartnerSummary, names: dict[uuid.UUID, str]) -> OwnerSummary | None:
    if partner.owner_id is None or partner.owner_id not in names:
        return None
    return OwnerSummary(id=partner.owner_id, name=names[partner.owner_id])


def _date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _codes(value: str | None) -> set[str]:
    return {code.strip() for code in (value or "").split(",") if code.strip()}


def _int(value: str | None) -> int | None:
    return int(value) if value else None


def _facts_read(facts: dict[str, str | None]) -> dict[str, object]:
    adjustments = facts.get("adjustments")
    return {
        "number": facts.get("number"),
        "signed_on": _date(facts.get("signed_on")),
        "effective_from": _date(facts.get("effective_from")),
        "effective_to": _date(facts.get("effective_to")),
        "adjustments": [Adjustment(a) for a in adjustments.split(",")] if adjustments else [],
        "summary": facts.get("summary"),
    }


def _is_locked(instrument: Instrument) -> bool:
    """Sent for approval or approved: the director's decision stays on record. A document only
    typed in (the archive, a scan entered by hand) can be removed when it was a mistake."""
    return instrument.review_state in (ReviewState.SUBMITTED, ReviewState.APPROVED)


def _require_review(instrument: Instrument, *allowed: ReviewState | None) -> None:
    if instrument.review_state not in allowed:
        raise ConflictError(
            "The document is not at a step that allows this",
            code=ErrorCode.REVIEW_STATE_INVALID,
        )


def _term_months(facts: dict[str, str | None]) -> int | None:
    """Without a stated cycle, an automatic renewal repeats the original term, counted in whole
    months from the start to the day after the end."""
    start = _date(facts.get("effective_from") or facts.get("signed_on"))
    end = _date(facts.get("expires_on"))
    if start is None or end is None:
        return None
    after = end + timedelta(days=1)
    months = (after.year - start.year) * 12 + after.month - start.month
    return months if months > 0 and after.day == start.day else None


def _event_read(event: ContractEvent, names: dict[uuid.UUID, str]) -> ContractEventRead:
    return ContractEventRead.model_validate(
        {
            "id": event.id,
            "kind": event.kind,
            "instrument_id": event.instrument_id,
            "instrument_code": event.instrument_code,
            "changes": event.changes or [],
            "signing_state": event.signing_state,
            "file_id": event.file_id,
            "comment": event.comment,
            "actor_id": event.actor_id,
            "actor_name": names.get(event.actor_id),
            "created_at": event.created_at,
        }
    )


# The dashboard's "soon": as far ahead as the earliest expiry warning used to be raised.
DUE_WINDOW_DAYS = 90


class ContractService:
    def __init__(
        self,
        session: AsyncSession,
        contracts: ContractRepository,
        instruments: InstrumentRepository,
        values: FieldValueRepository,
        events: ContractEventRepository,
        counters: CodeCounterRepository,
        documents: DocumentService,
        partners: PartnerService,
        users: UserService,
    ) -> None:
        self.session = session
        self.contracts = contracts
        self.instruments = instruments
        self.values = values
        self.events = events
        self.counters = counters
        self.documents = documents
        self.partners = partners
        self.users = users

    @staticmethod
    def field_specs() -> list[FieldSpecRead]:
        return [
            FieldSpecRead(
                key=s.key,
                type=s.type,
                instrument=s.instrument,
                is_key=s.is_key,
                choices=list(s.choices),
            )
            for s in FIELDS
        ]

    async def _load(self, contracts: Sequence[Contract]) -> list[_Loaded]:
        ids = [c.id for c in contracts]
        instruments = await self.instruments.of_contracts(ids)
        values: dict[uuid.UUID, list[FieldValue]] = defaultdict(list)
        for value in await self.values.current_of([i.id for i in instruments]):
            values[value.instrument_id].append(value)
        by_contract: dict[uuid.UUID, list[Instrument]] = defaultdict(list)
        for instrument in instruments:
            by_contract[instrument.contract_id].append(instrument)
        partners = await self.partners.summaries(list({c.partner_id for c in contracts}))
        names = await self.users.names({p.owner_id for p in partners.values() if p.owner_id})
        return [
            _Loaded(
                c,
                by_contract[c.id],
                values,
                partners[c.partner_id],
                _owner(partners[c.partner_id], names),
            )
            for c in contracts
        ]

    async def _get(self, contract_id: uuid.UUID) -> Contract:
        contract = await self.contracts.get(contract_id)
        if contract is None:
            raise NotFoundError("Contract not found")
        return contract

    async def _instrument(self, instrument_id: uuid.UUID) -> Instrument:
        instrument = await self.instruments.get(instrument_id)
        if instrument is None:
            raise NotFoundError("Document not found")
        return instrument

    async def list(self, params: ContractFilter) -> Page[ContractRead]:
        today = business_today()
        partner_ids = await self.partners.ids_matching(params.q) if params.q else None
        rows, total = await self.contracts.list_page(
            params, partner_ids, today, await self._owned_partner_ids(params)
        )
        return Page[ContractRead](
            items=[item.read(today) for item in await self._load(rows)],
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    async def _owned_partner_ids(
        self, params: ContractFilter | InstrumentFilter
    ) -> Sequence[uuid.UUID] | None:
        if params.owner_id is not None:
            return await self.partners.ids_owned(params.owner_id)
        if params.is_unassigned:
            return await self.partners.ids_owned(None)
        return None

    async def list_instruments(self, params: InstrumentFilter) -> Page[InstrumentListItem]:
        """Addenda, schedules and terminations across contracts, grouped by contract."""
        partner_ids = await self.partners.ids_matching(params.q) if params.q else None
        rows, total = await self.instruments.list_page(
            params, partner_ids, await self._owned_partner_ids(params)
        )
        partners = await self.partners.summaries(list({c.partner_id for _, c in rows}))
        names = await self.users.names({p.owner_id for p in partners.values() if p.owner_id})
        annex_counts = await self.instruments.count_annexes({c.id for _, c in rows})
        replaced_codes = await self.instruments.codes_of(
            {i.replaced_by_id for i, _ in rows if i.replaced_by_id}
        )
        return Page[InstrumentListItem](
            items=[
                InstrumentListItem(
                    id=i.id,
                    kind=i.kind,
                    code=i.code,
                    number=i.number,
                    signed_on=i.signed_on,
                    effective_from=i.effective_from,
                    effective_to=i.effective_to,
                    adjustments=[Adjustment(a) for a in i.adjustments.split(",")]
                    if i.adjustments
                    else [],
                    summary=i.summary,
                    review_state=i.review_state,
                    signing_state=i.signing_state,
                    standing=i.standing,
                    replaced_by_code=replaced_codes.get(i.replaced_by_id)
                    if i.replaced_by_id
                    else None,
                    missing_count=i.missing_count,
                    file_id=i.file_id,
                    contract_id=c.id,
                    contract_code=c.code,
                    contract_status=ContractStatus(c.status),
                    contract_annex_count=annex_counts.get(c.id, 0),
                    partner=partners[c.partner_id],
                    owner=_owner(partners[c.partner_id], names),
                )
                for i, c in rows
            ],
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    async def all_instruments(self, params: InstrumentFilter) -> Sequence[InstrumentListItem]:
        """Every page of `list_instruments`, for the export."""
        items: list[InstrumentListItem] = []
        page = 1
        while True:
            batch = await self.list_instruments(
                params.model_copy(update={"page": page, "page_size": _EXPORT_PAGE_SIZE})
            )
            items.extend(batch.items)
            if len(items) >= batch.total or not batch.items:
                return items
            page += 1

    async def refresh_all(self, on: date) -> int:
        """Re-derive every contract's stored status and end date for `on`; the nightly job runs
        this because a status changes with the date alone. Returns how many changed."""
        changed = 0
        after: uuid.UUID | None = None
        while rows := await self.contracts.batch_after(after, _REFRESH_BATCH):
            loaded = await self._load(rows)
            for item in loaded:
                await self._issue_code(item)
            changed += await self._store_derived(loaded, on)
            after = rows[-1].id
            await self.session.commit()
        return changed

    async def _store_derived(self, loaded: Sequence[_Loaded], on: date) -> int:
        changed = 0
        for item in loaded:
            read = item.read(on)
            derived = {
                "number": read.number,
                "signed_on": read.signed_on,
                "effective_from": read.effective_from,
                "end_on": read.end_on,
                "notice_on": read.notice_on,
                "status": read.status,
                "missing_count": read.missing_count,
                "renewal": read.renewal,
                "payment_days": read.payment_days,
                "payment_from": read.payment_from,
                "statement_cutoff": read.statement_cutoff,
            }
            if any(getattr(item.contract, k) != v for k, v in derived.items()):
                await self.contracts.update(item.contract, **derived)
                changed += 1
            standings = item.standings(on, read.status)
            for instrument in item.instruments:
                facts = item.facts(instrument)
                copied = {
                    "number": facts.get("number"),
                    "signed_on": _date(facts.get("signed_on")),
                    "effective_from": _date(facts.get("effective_from") or facts.get("signed_on")),
                    "effective_to": _date(facts.get("effective_to")),
                    "adjustments": facts.get("adjustments"),
                    "summary": facts.get("summary"),
                    "missing_count": len(item.missing(instrument)),
                    "standing": standings.get(instrument.id, (None, None))[0],
                    "replaced_by_id": standings.get(instrument.id, (None, None))[1],
                }
                if any(getattr(instrument, k) != v for k, v in copied.items()):
                    await self.instruments.update(instrument, **copied)
        return changed

    async def _commit(self, contract: Contract) -> None:
        """Refresh the stored copies of the contract's facts, then commit. A contract it
        re-signs ends the day before it takes effect, so that one follows its start date."""
        today = business_today()
        await self._store_derived(await self._load([contract]), today)
        older = [
            c
            for c in await self.contracts.replaced_by(contract.id)
            if c.replaced_on != contract.effective_from
        ]
        for previous in older:
            await self.contracts.update(previous, replaced_on=contract.effective_from)
        if older:
            await self._store_derived(await self._load(older), today)
        await self.session.commit()

    async def overview(self) -> ContractOverview:
        """Counts for the dashboard: contracts by status, documents waiting for a person, and
        contracts whose end or notice deadline is near."""
        approval, signature = await self.instruments.count_awaiting()
        today = business_today()
        return ContractOverview(
            by_status=[
                StatusCount(status=ContractStatus(status), count=count)
                for status, count in (await self.contracts.status_counts()).items()
            ],
            awaiting_approval=approval,
            awaiting_signature=signature,
            expiring_soon=await self.contracts.count_active_due("end_on", today, DUE_WINDOW_DAYS),
            notice_soon=await self.contracts.count_active_due("notice_on", today, DUE_WINDOW_DAYS),
        )

    async def read(self, contract_id: uuid.UUID, on: date | None = None) -> ContractRead:
        [loaded] = await self._load([await self._get(contract_id)])
        return loaded.read(on or business_today())

    async def instrument_scope(self, instrument_id: uuid.UUID) -> InstrumentScope:
        instrument = await self._instrument(instrument_id)
        contract = await self._get(instrument.contract_id)
        return InstrumentScope(
            id=instrument.id,
            contract_id=contract.id,
            side=PartnerRole(contract.side),
        )

    async def get(self, contract_id: uuid.UUID) -> ContractDetail:
        [loaded] = await self._load([await self._get(contract_id)])
        events = await self.events.of_contract(contract_id)
        names = await self.users.names(e.actor_id for e in events)
        proposed: dict[uuid.UUID, str] = {}
        approved: dict[uuid.UUID, str] = {}
        for event in events:
            target = {EventKind.SUBMITTED: proposed, EventKind.APPROVED: approved}.get(event.kind)
            if target is not None and event.instrument_id is not None:
                target[event.instrument_id] = names.get(event.actor_id, "")
        today = business_today()
        read = loaded.read(today)
        standings = loaded.standings(today, read.status)
        applying = loaded.applying(today, read.status)
        contract = loaded.contract
        previous = await self.contracts.replaced_by(contract.id)
        return ContractDetail.model_validate(
            {
                **read.model_dump(),
                "replaces": _ref(previous[0]) if previous else None,
                "replaced_by": _ref(await self._get(contract.replaced_by_id))
                if contract.replaced_by_id
                else None,
                "overlapping": [
                    _ref(other)
                    for other in await self.contracts.in_force_alongside(contract)
                    if other.id not in {p.id for p in previous}
                ]
                if read.lifecycle == Lifecycle.ACTIVE
                else [],
                "events": [_event_read(e, names) for e in events],
                "instruments": [
                    InstrumentRead.model_validate(
                        {
                            "id": i.id,
                            "kind": i.kind,
                            "code": i.code,
                            **_facts_read(loaded.facts(i)),
                            "review_state": i.review_state,
                            "signing_state": i.signing_state,
                            "proposed_by_name": proposed.get(i.id),
                            "approved_by_name": approved.get(i.id),
                            "is_settled": loaded.is_settled(i),
                            "standing": standings.get(i.id, (None, None))[0],
                            "replaced_by_code": next(
                                (
                                    o.code
                                    for o in loaded.instruments
                                    if o.id == standings.get(i.id, (None, None))[1]
                                ),
                                None,
                            ),
                            "file_id": i.file_id,
                            "values": [
                                FieldValueRead.model_validate(v)
                                for v in loaded.values.get(i.id, [])
                                if v.value is not None
                            ],
                            "missing": loaded.missing(i),
                            "can_delete": i.kind != InstrumentKind.CONTRACT and not _is_locked(i),
                        }
                    )
                    for i in loaded.in_order()
                ],
                "can_delete": not contract.is_imported
                and not any(_is_locked(i) for i in loaded.instruments),
                "applying": [
                    {
                        "kind": kind,
                        "instrument_id": i.id,
                        "code": i.code,
                        "effective_from": _date(loaded.facts(i).get("effective_from")),
                    }
                    for kind, i in sorted(applying.items())
                ],
            }
        )

    async def create(
        self, body: ContractCreate, filename: str, data: bytes, user_id: uuid.UUID
    ) -> ContractDetail:
        """A new contract with its contract document and file, all at once: nothing is left
        behind when any part fails, so no code is spent on an empty contract."""
        side = _SIDE_OF.get(body.category, body.side)
        if side is None:
            raise AppError(
                "Choose the side of the lease", code=ErrorCode.INVALID_FIELD_VALUE, field="side"
            )
        await self.partners.get(body.partner_id)
        previous = await self._replaced(body) if body.replaces_id else None
        dossier_id = await self.documents.create_set(DocumentSide(side), body.partner_id)
        stored = await self.documents.attach_file(dossier_id, filename, data)
        prefix = CODE_PREFIXES[body.category]
        year = business_today().year
        contract = await self.contracts.create(
            partner_id=body.partner_id,
            side=side,
            category=body.category,
            code=f"{prefix}-{year}-{await self.counters.next_number(prefix, year):04d}",
            dossier_id=dossier_id,
            created_by_id=user_id,
        )
        await self.events.create(contract_id=contract.id, kind=EventKind.CREATED, actor_id=user_id)
        await self.instruments.create(
            contract_id=contract.id,
            kind=InstrumentKind.CONTRACT,
            file_id=stored.id,
            created_by_id=user_id,
            review_state=ReviewState.DRAFT if body.needs_approval else None,
            signing_state=SigningState.UNSIGNED if body.needs_approval else SigningState.SIGNED,
        )
        if previous is not None:
            await self.contracts.update(previous, replaced_by_id=contract.id, replaced_on=None)
        [loaded] = await self._load([contract])
        await self._issue_code(loaded)
        await self._commit(contract)
        return await self.get(contract.id)

    async def _replaced(self, body: ContractCreate) -> Contract:
        """The contract being re-signed: same partner and category, not re-signed before."""
        assert body.replaces_id is not None
        previous = await self._get(body.replaces_id)
        if previous.partner_id != body.partner_id or previous.category != body.category:
            raise ConflictError(
                "A re-signed contract keeps its partner and category",
                code=ErrorCode.INVALID_FIELD_VALUE,
                field="replacesId",
            )
        if previous.replaced_by_id is not None:
            raise ConflictError(
                "This contract was already re-signed",
                code=ErrorCode.CONTRACT_ALREADY_RESIGNED,
                field="replacesId",
            )
        return previous

    async def import_archived(
        self,
        seed: ArchivedContract,
        dossier_id: uuid.UUID,
        file_ids: dict[str, uuid.UUID],
        actor_id: uuid.UUID,
    ) -> ArchivedImport:
        """Record a signed archive contract and its annexes from the seed. A contract is found
        again by its main file, a document by its file, so a re-run only adds what is new."""
        dossier = await self.documents.get(dossier_id)
        if dossier.partner is None:
            raise ValueError(f"Dossier {dossier_id} has no partner")
        main_file = file_ids[seed.document.sha256]
        existing = await self.instruments.list(
            Instrument.file_id == main_file, Instrument.kind == InstrumentKind.CONTRACT
        )
        if existing:
            contract = await self._get(existing[0].contract_id)
        else:
            facts = seed.document.facts
            year = int((facts.get("signed_on") or facts.get("effective_from") or "")[:4] or 0)
            year = year or business_today().year
            prefix = CODE_PREFIXES[seed.category]
            contract = await self.contracts.create(
                partner_id=dossier.partner.id,
                side=PartnerRole(dossier.side),
                category=seed.category,
                code=f"{prefix}-{year}-{await self.counters.next_number(prefix, year):04d}",
                dossier_id=dossier_id,
                is_imported=True,
                created_by_id=actor_id,
            )
            await self.events.create(
                contract_id=contract.id, kind=EventKind.IMPORTED, actor_id=actor_id
            )
        added, rejected = 0, []
        recorded = {i.file_id for i in await self.instruments.of_contracts([contract.id])}
        for document in [seed.document, *seed.annexes]:
            file_id = file_ids[document.sha256]
            if file_id in recorded:
                continue
            recorded.add(file_id)
            instrument = await self.instruments.create(
                contract_id=contract.id,
                kind=document.kind,
                file_id=file_id,
                created_by_id=actor_id,
                review_state=None,
                signing_state=SigningState.SIGNED,
            )
            added += 1
            for key, raw in document.facts.items():
                spec = SPECS.get((document.kind, key))
                if spec is None:
                    continue
                try:
                    value = normalize(spec, raw)
                except InvalidValueError:
                    value = None
                if value is None:
                    rejected.append(f"{document.sha256[:12]} {key}={raw}")
                    continue
                await self.values.create(
                    instrument_id=instrument.id, key=key, value=value, entered_by_id=actor_id
                )
        [loaded] = await self._load([contract])
        await self._issue_code(loaded)
        await self._commit(contract)
        return ArchivedImport(
            contract_id=contract.id,
            is_new=not existing,
            documents_added=added,
            rejected_facts=rejected,
        )

    async def mark_replaced(self, contract_id: uuid.UUID, successor_id: uuid.UUID) -> bool:
        """Record that `successor_id` re-signed `contract_id`: the older one ends the day before
        the newer one takes effect. Returns whether anything changed."""
        contract, successor = await self._get(contract_id), await self._get(successor_id)
        if successor.effective_from is None or contract.replaced_by_id == successor.id:
            return False
        await self.contracts.update(
            contract, replaced_by_id=successor.id, replaced_on=successor.effective_from
        )
        await self._commit(contract)
        return True

    async def _check_file(self, contract: Contract, file_id: uuid.UUID) -> None:
        try:
            await self.documents.file_of(contract.dossier_id, file_id)
        except NotFoundError as exc:
            raise ConflictError(
                "The file is not in this contract's dossier",
                code=ErrorCode.FILE_NOT_IN_DOSSIER,
                field="fileId",
            ) from exc

    async def add_instrument(
        self, contract_id: uuid.UUID, body: InstrumentCreate, user_id: uuid.UUID
    ) -> ContractDetail:
        contract = await self.contracts.lock(contract_id)
        if contract is None:
            raise NotFoundError("Contract not found")
        await self._check_file(contract, body.file_id)
        if (
            body.kind == InstrumentKind.CONTRACT
            and await self.instruments.main_of(contract.id) is not None
        ):
            raise ConflictError(
                "The contract document is already recorded",
                code=ErrorCode.INSTRUMENT_EXISTS,
                field="kind",
            )
        instrument = await self.instruments.create(
            contract_id=contract.id,
            kind=body.kind,
            file_id=body.file_id,
            created_by_id=user_id,
            review_state=ReviewState.DRAFT if body.needs_approval else None,
            signing_state=SigningState.UNSIGNED if body.needs_approval else SigningState.SIGNED,
        )
        [loaded] = await self._load([contract])
        await self._issue_code(loaded)
        await self.events.create(
            contract_id=contract.id,
            kind=EventKind.ADDED,
            instrument_id=instrument.id,
            instrument_code=instrument.code,
            file_id=body.file_id,
            actor_id=user_id,
        )
        await self._commit(contract)
        return await self.get(contract.id)

    async def delete_instrument(
        self, instrument_id: uuid.UUID, user_id: uuid.UUID
    ) -> ContractDetail:
        """Remove a document recorded by mistake, while it is still an unapproved, unsigned
        draft. Its code is not reused."""
        instrument = await self._instrument(instrument_id)
        contract = await self.contracts.lock(instrument.contract_id)
        if contract is None:
            raise NotFoundError("Contract not found")
        if instrument.kind == InstrumentKind.CONTRACT:
            raise ConflictError(
                "A contract keeps its contract document; delete the contract instead",
                code=ErrorCode.CONTRACT_DOCUMENT_REQUIRED,
            )
        if _is_locked(instrument):
            raise ConflictError(
                "A document sent for approval stays on record",
                code=ErrorCode.DOCUMENT_LOCKED,
            )
        await self.events.create(
            contract_id=contract.id,
            kind=EventKind.DELETED,
            instrument_code=instrument.code,
            file_id=instrument.file_id,
            comment=instrument.kind,
            actor_id=user_id,
        )
        await self.instruments.delete(instrument)
        await self._commit(contract)
        return await self.get(contract.id)

    async def delete(self, contract_id: uuid.UUID) -> None:
        """Remove a contract recorded by mistake: none of its documents was approved or signed.
        Its code is not reused; its dossier goes with it unless another contract shares it."""
        contract = await self.contracts.lock(contract_id)
        if contract is None:
            raise NotFoundError("Contract not found")
        if contract.is_imported:
            raise ConflictError(
                "A contract loaded from the archive stays on record",
                code=ErrorCode.CONTRACT_FROM_ARCHIVE,
            )
        if any(_is_locked(i) for i in await self.instruments.of_contracts([contract.id])):
            raise ConflictError(
                "A contract with a signed or approved document cannot be deleted",
                code=ErrorCode.CONTRACT_LOCKED,
            )
        dossier_id = contract.dossier_id
        await self.contracts.delete(contract)
        if await self.contracts.count_in_dossier(dossier_id) == 0:
            await self.documents.delete_set(dossier_id)
        await self.session.commit()

    async def remove_file(self, contract_id: uuid.UUID, file_id: uuid.UUID) -> None:
        """Take a file uploaded by mistake out of the contract's dossier."""
        contract = await self._get(contract_id)
        if await self.instruments.file_in_use(contract.dossier_id, file_id):
            raise ConflictError(
                "A document uses this file", code=ErrorCode.FILE_IN_USE, field="fileId"
            )
        await self.documents.remove_file(contract.dossier_id, file_id)
        await self.session.commit()

    async def write_facts(
        self, instrument_id: uuid.UUID, body: FactsWrite, user_id: uuid.UUID
    ) -> InstrumentRead:
        """Record the facts of a document in one go. A changed value supersedes the current one,
        which stays in the history; an empty value clears the field; unchanged ones are left."""
        instrument = await self._instrument(instrument_id)
        normalized: dict[str, str | None] = {}
        for key, raw in body.values.items():
            spec = SPECS.get((instrument.kind, key))
            if spec is None:
                raise AppError("Unknown field", code=ErrorCode.UNKNOWN_FIELD, field=f"values.{key}")
            normalized[key] = self._normalized(spec, raw, field=f"values.{key}")
        contract = await self._get(instrument.contract_id)
        changes: list[dict[str, str | None]] = []
        for key, value in normalized.items():
            current = await self.values.lock_current(instrument.id, key)
            before = current.value if current else None
            if before == value:
                continue
            if current is not None:
                await self.values.update(current, superseded_at=datetime.now(UTC))
            await self.values.create(
                instrument_id=instrument.id, key=key, value=value, entered_by_id=user_id
            )
            changes.append({"key": key, "before": before, "after": value})
        if changes:
            await self.events.create(
                contract_id=contract.id,
                kind=EventKind.EDITED,
                instrument_id=instrument.id,
                instrument_code=instrument.code,
                changes=changes,
                actor_id=user_id,
            )
        await self._commit(contract)
        detail = await self.get(contract.id)
        return next(i for i in detail.instruments if i.id == instrument.id)

    async def apply_facts(
        self, changes: dict[str, dict[str, str | None]], user_id: uuid.UUID
    ) -> tuple[str, ...]:
        """Record facts read back from the documents, keyed by document code, each as an edit in
        the history. Returns the codes no document carries."""
        unknown: tuple[str, ...] = ()
        for code, values in changes.items():
            found = await self.instruments.list(Instrument.code == code)
            if len(found) != 1:
                unknown += (code,)
                continue
            await self.write_facts(found[0].id, FactsWrite(values=values), user_id)
        return unknown

    @staticmethod
    def _normalized(spec: FieldSpec, raw: str | None, field: str = "value") -> str | None:
        if raw is None or not raw.strip():
            return None
        try:
            return normalize(spec, raw)
        except InvalidValueError as exc:
            raise AppError(
                "Invalid value for this field", code=ErrorCode.INVALID_FIELD_VALUE, field=field
            ) from exc

    async def _issue_code(self, loaded: _Loaded) -> None:
        """Give the contract its code if it has none (type, year recorded, running number) and
        number its documents. Idempotent, so the nightly refresh also codes older contracts."""
        contract, main = loaded.contract, loaded.main
        if contract.code is None:
            year = contract.created_at.year
            prefix = CODE_PREFIXES[ContractCategory(contract.category)]
            number = await self.counters.next_number(prefix, year)
            await self.contracts.update(contract, code=f"{prefix}-{year}-{number:04d}")
        if contract.code is not None:
            if main is not None and main.code is None:
                await self.instruments.update(main, code=contract.code)
            await self._number_annexes(contract, loaded.instruments)

    async def _number_annexes(self, contract: Contract, instruments: Sequence[Instrument]) -> None:
        """Give each addendum and schedule without a code the next PL number of the contract."""
        annexes = [i for i in instruments if i.kind in _ANNEXES]
        issued = sum(1 for i in annexes if i.code is not None)
        for instrument in annexes:
            if instrument.code is None:
                issued += 1
                await self.instruments.update(instrument, code=f"{contract.code}-PL{issued:02d}")

    async def submit(
        self, instrument_id: uuid.UUID, body: ReviewSubmit, user_id: uuid.UUID
    ) -> ContractDetail:
        """Send a Spider-drafted document for approval, optionally as a new version of the draft."""
        instrument = await self._instrument(instrument_id)
        _require_review(instrument, ReviewState.DRAFT, ReviewState.REJECTED)
        contract = await self._get(instrument.contract_id)
        if body.file_id is not None:
            await self._check_file(contract, body.file_id)
            await self.instruments.update(instrument, file_id=body.file_id)
        return await self._move(
            contract, instrument, ReviewState.SUBMITTED, EventKind.SUBMITTED, user_id, body.comment
        )

    async def approve(
        self, instrument_id: uuid.UUID, body: ReviewDecision, user_id: uuid.UUID
    ) -> ContractDetail:
        instrument = await self._instrument(instrument_id)
        _require_review(instrument, ReviewState.SUBMITTED)
        contract = await self._get(instrument.contract_id)
        return await self._move(
            contract, instrument, ReviewState.APPROVED, EventKind.APPROVED, user_id, body.comment
        )

    async def reject(
        self, instrument_id: uuid.UUID, body: ReviewDecision, user_id: uuid.UUID
    ) -> ContractDetail:
        instrument = await self._instrument(instrument_id)
        _require_review(instrument, ReviewState.SUBMITTED)
        if not (body.comment or "").strip():
            raise AppError(
                "Say what to change",
                code=ErrorCode.REVIEW_COMMENT_REQUIRED,
                field="comment",
            )
        contract = await self._get(instrument.contract_id)
        return await self._move(
            contract, instrument, ReviewState.REJECTED, EventKind.REJECTED, user_id, body.comment
        )

    async def _move(
        self,
        contract: Contract,
        instrument: Instrument,
        state: ReviewState,
        kind: EventKind,
        user_id: uuid.UUID,
        comment: str | None,
    ) -> ContractDetail:
        await self.instruments.update(instrument, review_state=state)
        await self.events.create(
            contract_id=contract.id,
            instrument_id=instrument.id,
            instrument_code=instrument.code,
            kind=kind,
            actor_id=user_id,
            comment=comment,
            # The version that was read: the signed copy is checked against it.
            file_id=instrument.file_id,
        )
        await self._commit(contract)
        return await self.get(contract.id)

    async def set_signing(
        self, instrument_id: uuid.UUID, body: SigningWrite, user_id: uuid.UUID
    ) -> ContractDetail:
        """Track signatures. A reviewed draft is signed only after approval, and marking it signed
        by both parties replaces the draft with the signed scan."""
        instrument = await self._instrument(instrument_id)
        _require_review(instrument, ReviewState.APPROVED, None)
        contract = await self._get(instrument.contract_id)
        if body.file_id is not None:
            await self._check_file(contract, body.file_id)
        elif (
            body.state == SigningState.SIGNED
            and instrument.review_state is not None
            and instrument.signing_state != SigningState.SIGNED
        ):
            raise AppError(
                "Attach the signed copy", code=ErrorCode.SIGNED_COPY_REQUIRED, field="fileId"
            )
        await self.instruments.update(
            instrument, signing_state=body.state, file_id=body.file_id or instrument.file_id
        )
        await self.events.create(
            contract_id=contract.id,
            instrument_id=instrument.id,
            instrument_code=instrument.code,
            kind=EventKind.SIGNING,
            signing_state=body.state,
            file_id=body.file_id,
            actor_id=user_id,
        )
        await self._commit(contract)
        return await self.get(contract.id)
