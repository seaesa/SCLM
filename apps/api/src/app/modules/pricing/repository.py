import uuid
from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy import ColumnElement, select

from app.modules.pricing.models import FuelClause, FuelPrice, PriceLine, PriceTable
from app.modules.pricing.schemas import FuelPriceFilter
from app.shared.repository import BaseRepository


class PriceTableRepository(BaseRepository[PriceTable]):
    model = PriceTable

    async def current_of(self, contract_ids: Sequence[uuid.UUID]) -> Sequence[PriceTable]:
        return await self.list(
            PriceTable.contract_id.in_(contract_ids),
            PriceTable.withdrawn_at.is_(None),
            order_by=[PriceTable.effective_from, PriceTable.created_at],
        )


class PriceLineRepository(BaseRepository[PriceLine]):
    model = PriceLine

    async def current_of(self, table_ids: Sequence[uuid.UUID]) -> Sequence[PriceLine]:
        return await self.list(
            PriceLine.table_id.in_(table_ids),
            PriceLine.withdrawn_at.is_(None),
            order_by=[PriceLine.created_at, PriceLine.id],
        )


class FuelClauseRepository(BaseRepository[FuelClause]):
    model = FuelClause

    async def current_of(self, contract_id: uuid.UUID) -> Sequence[FuelClause]:
        return await self.list(
            FuelClause.contract_id == contract_id,
            FuelClause.withdrawn_at.is_(None),
            order_by=[FuelClause.base_on, FuelClause.created_at],
        )


class FuelPriceRepository(BaseRepository[FuelPrice]):
    model = FuelPrice

    async def list_page(self, params: FuelPriceFilter) -> tuple[Sequence[FuelPrice], int]:
        """Latest price first."""
        filters: list[ColumnElement[bool]] = []
        if params.fuel_type:
            filters.append(FuelPrice.fuel_type == params.fuel_type)
        return await self.page(
            self._select(*filters),
            [FuelPrice.effective_on.desc(), FuelPrice.fuel_type, FuelPrice.id],
            params.offset,
            params.page_size,
        )

    async def series(self, fuel_type: str, after: date, until: date) -> list[tuple[date, Decimal]]:
        query = (
            select(FuelPrice.effective_on, FuelPrice.price)
            .where(
                FuelPrice.fuel_type == fuel_type,
                FuelPrice.effective_on > after,
                FuelPrice.effective_on <= until,
            )
            .order_by(FuelPrice.effective_on)
        )
        return [(row[0], row[1]) for row in await self.session.execute(query)]

    async def on_date(self, fuel_type: str, effective_on: date) -> FuelPrice | None:
        found: FuelPrice | None = await self.find_one(
            FuelPrice.fuel_type == fuel_type, FuelPrice.effective_on == effective_on
        )
        return found
