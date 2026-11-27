import uuid
from collections.abc import Sequence
from datetime import date, timedelta
from typing import Any

from sqlalchemy import ColumnElement, exists, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import InstrumentedAttribute

from app.modules.contracts.fields import MONTH_END, Renewal
from app.modules.contracts.models import (
    CodeCounter,
    Contract,
    ContractEvent,
    FieldValue,
    Instrument,
    InstrumentKind,
    ReviewState,
    SigningState,
)
from app.modules.contracts.schemas import (
    ContractFilter,
    ContractSort,
    InstrumentFilter,
    InstrumentWorkflow,
    PaymentFilter,
    RenewalFilter,
    StatementFilter,
)
from app.modules.contracts.timeline import LIFECYCLE_STATUSES, ContractStatus, Lifecycle
from app.shared.repository import BaseRepository


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# Approved, or needing no approval, but not yet signed by both parties.
# The documents listed as addenda: everything but the contract document itself.
_ANNEX_KINDS = (InstrumentKind.SCHEDULE, InstrumentKind.ADDENDUM, InstrumentKind.TERMINATION)

_AWAITING_SIGNATURE = or_(
    Instrument.review_state.is_(None), Instrument.review_state == ReviewState.APPROVED
) & (Instrument.signing_state != SigningState.SIGNED)


_RENEWAL_FILTERS: dict[RenewalFilter, ColumnElement[bool]] = {
    RenewalFilter.AUTOMATIC: Contract.renewal == Renewal.AUTOMATIC,
    RenewalFilter.IN_CYCLE: Contract.status == ContractStatus.AUTO_RENEWED,
    RenewalFilter.CONDITIONAL: Contract.renewal == Renewal.CONDITIONAL,
    RenewalFilter.NONE: or_(Contract.renewal.is_(None), Contract.renewal == Renewal.NONE),
}


_PAYMENT_FILTERS: dict[PaymentFilter, ColumnElement[bool]] = {
    PaymentFilter.UP_TO_15: Contract.payment_days <= 15,
    PaymentFilter.UP_TO_30: Contract.payment_days.between(16, 30),
    PaymentFilter.UP_TO_45: Contract.payment_days.between(31, 45),
    PaymentFilter.OVER_45: Contract.payment_days > 45,
    PaymentFilter.NONE: Contract.payment_days.is_(None),
}
_STATEMENT_FILTERS: dict[StatementFilter, ColumnElement[bool]] = {
    StatementFilter.MONTH_END: Contract.statement_cutoff == MONTH_END,
    StatementFilter.DAY_OF_MONTH: Contract.statement_cutoff != MONTH_END,
    StatementFilter.NONE: Contract.statement_cutoff.is_(None),
}


class ContractRepository(BaseRepository[Contract]):
    model = Contract

    async def count_in_dossier(self, dossier_id: uuid.UUID) -> int:
        return (
            await self.session.scalar(select(func.count()).where(Contract.dossier_id == dossier_id))
            or 0
        )

    async def list_page(
        self,
        params: ContractFilter,
        partner_ids: Sequence[uuid.UUID] | None,
        today: date,
        owned_partner_ids: Sequence[uuid.UUID] | None = None,
    ) -> tuple[Sequence[Contract], int]:
        """`partner_ids` are the partners whose name matches `params.q`, and `owned_partner_ids`
        those of the owner asked for (or of nobody), both found by the caller."""
        filters: list[ColumnElement[bool]] = []
        if owned_partner_ids is not None:
            filters.append(Contract.partner_id.in_(owned_partner_ids))
        if params.q:
            pattern = f"%{_escape_like(params.q)}%"
            filters.append(
                or_(
                    Contract.code.ilike(pattern, escape="\\"),
                    Contract.number.ilike(pattern, escape="\\"),
                    Contract.partner_id.in_(partner_ids or ()),
                    # A contract is also found by the code or number of one of its documents.
                    exists().where(
                        Instrument.contract_id == Contract.id,
                        or_(
                            Instrument.code.ilike(pattern, escape="\\"),
                            Instrument.number.ilike(pattern, escape="\\"),
                        ),
                    ),
                )
            )
        if params.categories:
            filters.append(Contract.category.in_(params.categories))
        if params.lifecycle is not None:
            filters.append(Contract.status.in_(LIFECYCLE_STATUSES[params.lifecycle]))
        if params.partner_id is not None:
            filters.append(Contract.partner_id == params.partner_id)
        if params.dossier_id is not None:
            filters.append(Contract.dossier_id == params.dossier_id)
        for column, start, end in (
            (Contract.signed_on, params.signed_from, params.signed_to),
            (Contract.end_on, params.end_from, params.end_to),
            (Contract.notice_on, params.notice_from, params.notice_to),
        ):
            if start is not None:
                filters.append(column >= start)
            if end is not None:
                filters.append(column <= end)
        if params.renewal is not None:
            filters.append(_RENEWAL_FILTERS[params.renewal])
        if params.payments:
            filters.append(or_(*(_PAYMENT_FILTERS[p] for p in params.payments)))
        if params.statements:
            filters.append(or_(*(_STATEMENT_FILTERS[p] for p in params.statements)))
        if params.is_awaiting_approval is not None:
            awaiting = exists().where(
                Instrument.contract_id == Contract.id,
                Instrument.review_state == ReviewState.SUBMITTED,
            )
            filters.append(awaiting if params.is_awaiting_approval else ~awaiting)
        if params.is_awaiting_signature is not None:
            unsigned = exists().where(Instrument.contract_id == Contract.id, _AWAITING_SIGNATURE)
            filters.append(unsigned if params.is_awaiting_signature else ~unsigned)
        if params.is_incomplete is not None:
            incomplete = or_(
                Contract.missing_count > 0, Contract.status == ContractStatus.UNDETERMINED
            )
            filters.append(incomplete if params.is_incomplete else ~incomplete)
        orders: dict[ContractSort, list[ColumnElement[Any] | InstrumentedAttribute[Any]]] = {
            # A contract's own date, not when it was keyed in: the archive was loaded at once.
            ContractSort.NEWEST: [
                func.coalesce(Contract.signed_on, Contract.effective_from).desc().nulls_last(),
                Contract.created_at.desc(),
                Contract.id.desc(),
            ],
            ContractSort.NOTICE_ON: [Contract.notice_on.asc().nulls_last(), Contract.id],
            ContractSort.END_ON: [Contract.end_on.asc().nulls_last(), Contract.id],
            ContractSort.CODE: [Contract.code.asc().nulls_last(), Contract.id],
        }
        return await self.page(
            self._select(*filters), orders[params.sort], params.offset, params.page_size
        )

    async def replaced_by(self, successor_id: uuid.UUID) -> Sequence[Contract]:
        return await self.list(Contract.replaced_by_id == successor_id)

    async def in_force_alongside(self, contract: Contract) -> Sequence[Contract]:
        """Other in-force contracts of the same partner and category whose term overlaps."""
        filters: list[ColumnElement[bool]] = [
            Contract.partner_id == contract.partner_id,
            Contract.category == contract.category,
            Contract.id != contract.id,
            Contract.status.in_(LIFECYCLE_STATUSES[Lifecycle.ACTIVE]),
            # Neither is recorded as re-signing the other.
            or_(Contract.replaced_by_id.is_(None), Contract.replaced_by_id != contract.id),
        ]
        if contract.replaced_by_id is not None:
            filters.append(Contract.id != contract.replaced_by_id)
        if contract.end_on is not None:
            filters.append(
                or_(Contract.effective_from.is_(None), Contract.effective_from <= contract.end_on)
            )
        if contract.effective_from is not None:
            filters.append(
                or_(Contract.end_on.is_(None), Contract.end_on >= contract.effective_from)
            )
        return await self.list(*filters, order_by=[Contract.effective_from])

    async def batch_after(self, after: uuid.UUID | None, limit: int) -> Sequence[Contract]:
        filters: list[ColumnElement[bool]] = []
        if after is not None:
            filters.append(Contract.id > after)
        return await self.list(*filters, order_by=[Contract.id], limit=limit)

    async def count_active_due(self, column: str, today: date, days: int) -> int:
        """In-force contracts whose `end_on` or `notice_on` falls within `days` from today."""
        due = getattr(Contract, column)
        stmt = select(func.count()).where(
            Contract.status.in_(LIFECYCLE_STATUSES[Lifecycle.ACTIVE]),
            due.between(today, today + timedelta(days=days)),
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def status_counts(self) -> dict[str, int]:
        stmt = select(Contract.status, func.count()).group_by(Contract.status)
        rows = (await self.session.execute(stmt)).all()
        return {row[0]: row[1] for row in rows}

    async def of_partner(self, partner_id: uuid.UUID, side: str) -> Sequence[Contract]:
        return await self.list(Contract.partner_id == partner_id, Contract.side == side)

    async def lock(self, contract_id: uuid.UUID) -> Contract | None:
        """Row-locks the contract so codes and PL numbers are issued one at a time."""
        query = select(Contract).where(Contract.id == contract_id).with_for_update()
        return (await self.session.scalars(query)).one_or_none()


class CodeCounterRepository(BaseRepository[CodeCounter]):
    model = CodeCounter

    async def next_number(self, prefix: str, year: int) -> int:
        """Atomically issue the next number of a series; concurrent callers never share one."""
        stmt = (
            insert(CodeCounter)
            .values(prefix=prefix, year=year, last_number=1)
            .on_conflict_do_update(
                index_elements=[CodeCounter.prefix, CodeCounter.year],
                set_={"last_number": CodeCounter.last_number + 1},
            )
            .returning(CodeCounter.last_number)
        )
        return (await self.session.execute(stmt)).scalar_one()


class InstrumentRepository(BaseRepository[Instrument]):
    model = Instrument

    async def of_contracts(self, contract_ids: Sequence[uuid.UUID]) -> Sequence[Instrument]:
        return await self.list(
            Instrument.contract_id.in_(contract_ids),
            order_by=[Instrument.created_at, Instrument.id],
        )

    async def file_in_use(self, dossier_id: uuid.UUID, file_id: uuid.UUID) -> bool:
        """Whether a document of any contract kept in this dossier is that file."""
        return bool(
            await self.session.scalar(
                select(
                    exists().where(
                        Instrument.file_id == file_id,
                        Instrument.contract_id == Contract.id,
                        Contract.dossier_id == dossier_id,
                    )
                )
            )
        )

    async def main_of(self, contract_id: uuid.UUID) -> Instrument | None:
        return await self.find_one(
            Instrument.contract_id == contract_id, Instrument.kind == InstrumentKind.CONTRACT
        )

    async def list_page(
        self,
        params: InstrumentFilter,
        partner_ids: Sequence[uuid.UUID] | None,
        owned_partner_ids: Sequence[uuid.UUID] | None,
    ) -> tuple[Sequence[tuple[Instrument, Contract]], int]:
        """Documents across contracts, grouped by contract (its code), each contract's documents
        in the order they were recorded (PL01, PL02...)."""
        filters: list[ColumnElement[bool]] = [
            Instrument.kind == params.kind if params.kind else Instrument.kind.in_(_ANNEX_KINDS)
        ]
        if params.q:
            pattern = f"%{_escape_like(params.q)}%"
            filters.append(
                or_(
                    Instrument.code.ilike(pattern, escape="\\"),
                    Instrument.number.ilike(pattern, escape="\\"),
                    Contract.partner_id.in_(partner_ids or ()),
                )
            )
        if owned_partner_ids is not None:
            filters.append(Contract.partner_id.in_(owned_partner_ids))
        if params.contract_id is not None:
            filters.append(Instrument.contract_id == params.contract_id)
        if params.workflow == InstrumentWorkflow.AWAITING_APPROVAL:
            filters.append(Instrument.review_state == ReviewState.SUBMITTED)
        if params.workflow == InstrumentWorkflow.AWAITING_SIGNATURE:
            filters.append(_AWAITING_SIGNATURE)
        if params.adjustment is not None:
            filters.append(Instrument.adjustments.contains(params.adjustment))
        if params.standing is not None:
            filters.append(Instrument.standing == params.standing)
        if params.is_incomplete is not None:
            filters.append(
                Instrument.missing_count > 0
                if params.is_incomplete
                else Instrument.missing_count == 0
            )
        if params.effective_from is not None:
            filters.append(Instrument.effective_from >= params.effective_from)
        if params.effective_to is not None:
            filters.append(Instrument.effective_from <= params.effective_to)
        stmt = (
            select(Instrument, Contract)
            .join(Contract, Contract.id == Instrument.contract_id)
            .where(*filters)
        )
        total = await self.session.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = await self.session.execute(
            stmt.order_by(
                Contract.code.asc().nulls_last(),
                Contract.id,
                # Newest first inside a contract: the latest change is what people look for.
                Instrument.effective_from.desc().nulls_last(),
                Instrument.created_at.desc(),
                Instrument.id,
            )
            .offset(params.offset)
            .limit(params.page_size)
        )
        return [(i, c) for i, c in rows.all()], total or 0

    async def codes_of(self, instrument_ids: set[uuid.UUID]) -> dict[uuid.UUID, str | None]:
        if not instrument_ids:
            return {}
        rows = await self.session.execute(
            select(Instrument.id, Instrument.code).where(Instrument.id.in_(instrument_ids))
        )
        return {row[0]: row[1] for row in rows.all()}

    async def count_annexes(self, contract_ids: set[uuid.UUID]) -> dict[uuid.UUID, int]:
        if not contract_ids:
            return {}
        rows = await self.session.execute(
            select(Instrument.contract_id, func.count())
            .where(
                Instrument.contract_id.in_(contract_ids),
                Instrument.kind.in_((InstrumentKind.ADDENDUM, InstrumentKind.SCHEDULE)),
            )
            .group_by(Instrument.contract_id)
        )
        return {row[0]: row[1] for row in rows.all()}

    async def count_awaiting(self) -> tuple[int, int]:
        """Documents waiting for approval, and approved documents waiting for signatures."""
        approval = await self.session.scalar(
            select(func.count()).where(Instrument.review_state == ReviewState.SUBMITTED)
        )
        signature = await self.session.scalar(select(func.count()).where(_AWAITING_SIGNATURE))
        return approval or 0, signature or 0


class FieldValueRepository(BaseRepository[FieldValue]):
    model = FieldValue

    async def current_of(self, instrument_ids: Sequence[uuid.UUID]) -> Sequence[FieldValue]:
        return await self.list(
            FieldValue.instrument_id.in_(instrument_ids),
            FieldValue.superseded_at.is_(None),
            order_by=[FieldValue.key],
        )

    async def lock_current(self, instrument_id: uuid.UUID, key: str) -> FieldValue | None:
        """Row-locks the current reading so two people correcting at once cannot both win."""
        query = (
            select(FieldValue)
            .where(
                FieldValue.instrument_id == instrument_id,
                FieldValue.key == key,
                FieldValue.superseded_at.is_(None),
            )
            .with_for_update()
        )
        return (await self.session.scalars(query)).one_or_none()


class ContractEventRepository(BaseRepository[ContractEvent]):
    model = ContractEvent

    async def of_contract(self, contract_id: uuid.UUID) -> Sequence[ContractEvent]:
        return await self.list(
            ContractEvent.contract_id == contract_id,
            order_by=[ContractEvent.created_at, ContractEvent.id],
        )
