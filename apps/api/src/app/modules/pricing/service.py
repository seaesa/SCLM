import uuid
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.modules.contracts.schemas import InstrumentScope
from app.modules.contracts.service import ContractService
from app.modules.partners.schemas import PartnerRole
from app.modules.pricing.models import FuelClause, FuelPrice, PriceLine, PriceTable
from app.modules.pricing.petrolimex import FuelPriceSource
from app.modules.pricing.repository import (
    FuelClauseRepository,
    FuelPriceRepository,
    PriceLineRepository,
    PriceTableRepository,
)
from app.modules.pricing.rules import FuelClause as ClauseTerms
from app.modules.pricing.rules import (
    PriceKey,
    Table,
    governing_lines,
    previous_lines,
    price_change,
    price_key,
    propose,
)
from app.modules.pricing.schemas import (
    AdjustedLine,
    ComparedLineRead,
    ContractPricing,
    FuelAdjustment,
    FuelClauseRead,
    FuelClauseWrite,
    FuelPriceFilter,
    FuelPriceRead,
    FuelPriceSyncReport,
    FuelPriceWrite,
    FuelProposalRead,
    PriceLineCorrection,
    PriceLineRead,
    PriceLinesCreate,
    PriceLineWrite,
    PriceTableRead,
    PriceTableSummary,
    PriceTableWrite,
    WithdrawRequest,
)
from app.shared.permissions import Permission
from app.shared.schemas import ErrorCode, Page

_PRICE_PERMISSION = {
    PartnerRole.CUSTOMER: Permission.SELL_PRICES_READ,
    PartnerRole.SUPPLIER: Permission.BUY_PRICES_READ,
}

type Permissions = frozenset[Permission]


def _check_side(side: PartnerRole | str, permissions: Permissions) -> None:
    """Selling prices and buying prices are seen by different people."""
    if _PRICE_PERMISSION[PartnerRole(side)] not in permissions:
        raise ForbiddenError("Missing permission for these prices", code=ErrorCode.FORBIDDEN)


def _key(line: PriceLine) -> PriceKey:
    return price_key(line.service, line.origin, line.destination, line.vehicle, line.unit)


def _rule_table(table: PriceTable, lines: Sequence[PriceLine]) -> Table[PriceLine]:
    return Table(
        effective_from=table.effective_from,
        effective_to=table.effective_to,
        mode=table.mode,
        created_at=table.created_at,
        lines=[(_key(line), line) for line in lines],
    )


def _compared(
    lines: Sequence[PriceLine], previous: dict[PriceKey, PriceLine]
) -> list[ComparedLineRead]:
    result = []
    for line in lines:
        before = previous.get(_key(line))
        result.append(
            ComparedLineRead.model_validate(
                {
                    **PriceLineRead.model_validate(line).model_dump(),
                    "previous_price": before.unit_price if before else None,
                    "change": price_change(before.unit_price, line.unit_price) if before else None,
                }
            )
        )
    return result


class PricingService:
    def __init__(
        self,
        session: AsyncSession,
        tables: PriceTableRepository,
        lines: PriceLineRepository,
        clauses: FuelClauseRepository,
        fuel_prices: FuelPriceRepository,
        contracts: ContractService,
    ) -> None:
        self.session = session
        self.tables = tables
        self.lines = lines
        self.clauses = clauses
        self.fuel_prices = fuel_prices
        self.contracts = contracts

    async def _scope(self, instrument_id: uuid.UUID, permissions: Permissions) -> InstrumentScope:
        scope = await self.contracts.instrument_scope(instrument_id)
        _check_side(scope.side, permissions)
        return scope

    async def _withdraw(
        self,
        row: PriceTable | PriceLine | FuelClause,
        scope: InstrumentScope,
        body: WithdrawRequest,
        user_id: uuid.UUID,
    ) -> None:
        if row.withdrawn_at is not None:
            raise ConflictError("Already withdrawn", code=ErrorCode.ALREADY_WITHDRAWN)
        row.withdrawn_at = datetime.now(UTC)
        row.withdrawn_by_id = user_id
        row.withdraw_reason = body.reason

    async def _tables_with_lines(
        self, contract_ids: Sequence[uuid.UUID]
    ) -> list[tuple[PriceTable, list[PriceLine]]]:
        tables = await self.tables.current_of(contract_ids)
        by_table: dict[uuid.UUID, list[PriceLine]] = defaultdict(list)
        for line in await self.lines.current_of([t.id for t in tables]):
            by_table[line.table_id].append(line)
        return [(t, by_table[t.id]) for t in tables]

    # Contract price tables

    async def contract_pricing(
        self, contract_id: uuid.UUID, permissions: Permissions
    ) -> ContractPricing:
        contract = await self.contracts.read(contract_id)
        _check_side(contract.side, permissions)
        loaded = await self._tables_with_lines([contract_id])
        tables = {t.id: _rule_table(t, lines) for t, lines in loaded}
        return ContractPricing(
            tables=[
                PriceTableRead.model_validate(
                    {
                        **PriceTableSummary.model_validate(t).model_dump(),
                        "lines": _compared(
                            lines, previous_lines(list(tables.values()), tables[t.id])
                        ),
                    }
                )
                for t, lines in loaded
            ],
            fuel_clauses=[
                FuelClauseRead.model_validate(c) for c in await self.clauses.current_of(contract_id)
            ],
        )

    async def add_table(
        self, body: PriceTableWrite, user_id: uuid.UUID, permissions: Permissions
    ) -> PriceTableSummary:
        scope = await self._scope(body.instrument_id, permissions)
        if body.effective_to is not None and body.effective_to < body.effective_from:
            raise AppError(
                "The table ends before it starts",
                code=ErrorCode.INVALID_FIELD_VALUE,
                field="effectiveTo",
            )
        table = await self.tables.create(
            **body.model_dump(), contract_id=scope.contract_id, created_by_id=user_id
        )
        await self.session.commit()
        return PriceTableSummary.model_validate(table)

    async def _table(
        self, table_id: uuid.UUID, permissions: Permissions
    ) -> tuple[PriceTable, InstrumentScope]:
        table = await self.tables.get(table_id)
        if table is None:
            raise NotFoundError("Price table not found")
        return table, await self._scope(table.instrument_id, permissions)

    async def withdraw_table(
        self,
        table_id: uuid.UUID,
        body: WithdrawRequest,
        user_id: uuid.UUID,
        permissions: Permissions,
    ) -> None:
        table, scope = await self._table(table_id, permissions)
        await self._withdraw(table, scope, body, user_id)
        await self.session.commit()

    async def _new_lines(
        self,
        table: PriceTable,
        scope: InstrumentScope,
        lines: Sequence[PriceLineWrite],
        user_id: uuid.UUID,
    ) -> list[PriceLine]:
        if table.withdrawn_at is not None:
            raise ConflictError("The table was withdrawn", code=ErrorCode.ALREADY_WITHDRAWN)
        created = []
        for line in lines:
            values = line.model_dump(exclude={"reason"})
            created.append(
                await self.lines.create(**values, table_id=table.id, created_by_id=user_id)
            )
        return created

    async def add_lines(
        self,
        table_id: uuid.UUID,
        body: PriceLinesCreate,
        user_id: uuid.UUID,
        permissions: Permissions,
    ) -> list[PriceLineRead]:
        table, scope = await self._table(table_id, permissions)
        created = await self._new_lines(table, scope, body.lines, user_id)
        await self.session.commit()
        return [PriceLineRead.model_validate(line) for line in created]

    async def _line(
        self, line_id: uuid.UUID, permissions: Permissions
    ) -> tuple[PriceLine, PriceTable, InstrumentScope]:
        line = await self.lines.get(line_id)
        if line is None:
            raise NotFoundError("Price line not found")
        table, scope = await self._table(line.table_id, permissions)
        return line, table, scope

    async def correct_line(
        self,
        line_id: uuid.UUID,
        body: PriceLineCorrection,
        user_id: uuid.UUID,
        permissions: Permissions,
    ) -> PriceLineRead:
        """Withdraws the line and records the corrected one, so the old price stays on file."""
        line, table, scope = await self._line(line_id, permissions)
        await self._withdraw(line, scope, WithdrawRequest(reason=body.reason), user_id)
        [created] = await self._new_lines(table, scope, [body], user_id)
        await self.session.commit()
        return PriceLineRead.model_validate(created)

    async def withdraw_line(
        self,
        line_id: uuid.UUID,
        body: WithdrawRequest,
        user_id: uuid.UUID,
        permissions: Permissions,
    ) -> None:
        line, _, scope = await self._line(line_id, permissions)
        await self._withdraw(line, scope, body, user_id)
        await self.session.commit()

    # Fuel clauses

    async def add_fuel_clause(
        self, body: FuelClauseWrite, user_id: uuid.UUID, permissions: Permissions
    ) -> FuelClauseRead:
        scope = await self._scope(body.instrument_id, permissions)
        clause = await self.clauses.create(
            **body.model_dump(), contract_id=scope.contract_id, created_by_id=user_id
        )
        await self.session.commit()
        return FuelClauseRead.model_validate(clause)

    async def withdraw_fuel_clause(
        self,
        clause_id: uuid.UUID,
        body: WithdrawRequest,
        user_id: uuid.UUID,
        permissions: Permissions,
    ) -> None:
        clause = await self.clauses.get(clause_id)
        if clause is None:
            raise NotFoundError("Fuel clause not found")
        scope = await self._scope(clause.instrument_id, permissions)
        await self._withdraw(clause, scope, body, user_id)
        await self.session.commit()

    # Lookup and adjustment

    async def _governing(
        self, contract_ids: Sequence[uuid.UUID], on: date
    ) -> list[tuple[PriceLine, PriceTable, bool]]:
        # Tables of different contracts never replace each other.
        by_contract: dict[uuid.UUID, list[Table[tuple[PriceLine, PriceTable]]]] = defaultdict(list)
        for table, lines in await self._tables_with_lines(contract_ids):
            by_contract[table.contract_id].append(
                Table(
                    effective_from=table.effective_from,
                    effective_to=table.effective_to,
                    mode=table.mode,
                    created_at=table.created_at,
                    lines=[(_key(line), (line, table)) for line in lines],
                )
            )
        return [
            (g.line[0], g.line[1], g.is_lapsed)
            for group in by_contract.values()
            for g in governing_lines(group, on)
        ]

    async def fuel_adjustment(
        self, contract_id: uuid.UUID, on: date, permissions: Permissions
    ) -> FuelAdjustment:
        contract = await self.contracts.read(contract_id, on)
        _check_side(contract.side, permissions)
        clauses = await self.clauses.current_of(contract_id)
        if not clauses:
            return FuelAdjustment(clause=None, proposal=None, lines=[])
        # The latest base governs: each fuel addendum resets it.
        clause = clauses[-1]
        terms = ClauseTerms(
            base_price=clause.base_price,
            base_on=clause.base_on,
            share=clause.share,
            threshold=clause.threshold,
            lag_days=clause.lag_days,
            rounding=clause.rounding,
            is_cumulative=clause.is_cumulative,
        )
        series = await self.fuel_prices.series(clause.fuel_type, clause.base_on, on)
        proposal = propose(terms, series, on)
        if proposal is None:
            return FuelAdjustment(
                clause=FuelClauseRead.model_validate(clause), proposal=None, lines=[]
            )
        governing = await self._governing([contract_id], on)
        return FuelAdjustment(
            clause=FuelClauseRead.model_validate(clause),
            proposal=FuelProposalRead(
                fuel_on=proposal.fuel_on,
                fuel_price=proposal.fuel_price,
                reference_price=proposal.reference_price,
                change=proposal.change,
                factor=proposal.factor,
                effective_on=proposal.effective_on,
            ),
            lines=[
                AdjustedLine(
                    line=PriceLineRead.model_validate(line),
                    proposed_price=proposal.adjust(line.unit_price, clause.rounding),
                )
                for line, _, is_lapsed in governing
                if not is_lapsed
            ],
        )

    # Fuel price index

    async def list_fuel_prices(self, params: FuelPriceFilter) -> Page[FuelPriceRead]:
        rows, total = await self.fuel_prices.list_page(params)
        return Page[FuelPriceRead](
            items=[FuelPriceRead.model_validate(r) for r in rows],
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    async def add_fuel_price(self, body: FuelPriceWrite, user_id: uuid.UUID) -> FuelPriceRead:
        if await self.fuel_prices.on_date(body.fuel_type, body.effective_on):
            raise ConflictError(
                "A price is already recorded for this fuel on this date",
                code=ErrorCode.FUEL_PRICE_EXISTS,
                field="effectiveOn",
            )
        price = await self.fuel_prices.create(**body.model_dump(), created_by_id=user_id)
        await self.session.commit()
        return FuelPriceRead.model_validate(price)

    async def sync_fuel_prices(self, source: FuelPriceSource) -> FuelPriceSyncReport:
        """Record the prices the source publishes now; the official price wins over a typed one."""
        report = FuelPriceSyncReport(added=0, updated=0, unchanged=0)
        for published in await source.fetch():
            known = await self.fuel_prices.on_date(published.fuel_type, published.effective_on)
            if known is None:
                await self.fuel_prices.create(
                    fuel_type=published.fuel_type,
                    effective_on=published.effective_on,
                    price=published.price,
                    source=source.name,
                    created_by_id=None,
                )
                report.added += 1
            elif known.price != published.price or known.source != source.name:
                known.price = published.price
                known.source = source.name
                known.created_by_id = None
                report.updated += 1
            else:
                report.unchanged += 1
        await self.session.commit()
        return report

    async def delete_fuel_price(self, price_id: uuid.UUID) -> None:
        price: FuelPrice | None = await self.fuel_prices.get(price_id)
        if price is None:
            raise NotFoundError("Fuel price not found")
        if price.created_by_id is None:
            raise ConflictError(
                "Prices synced from Petrolimex cannot be deleted",
                code=ErrorCode.OFFICIAL_PRICE_LOCKED,
            )
        await self.fuel_prices.delete(price)
        await self.session.commit()
