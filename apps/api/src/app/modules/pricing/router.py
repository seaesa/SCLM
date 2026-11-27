import uuid
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Path, Query, status

from app.modules.auth.dependencies import require_permission
from app.modules.pricing.petrolimex import FuelPriceSource
from app.modules.pricing.schemas import (
    ContractPricing,
    FuelAdjustment,
    FuelAdjustmentParams,
    FuelClauseRead,
    FuelClauseWrite,
    FuelPriceFilter,
    FuelPriceRead,
    FuelPriceSyncReport,
    FuelPriceWrite,
    PriceLineCorrection,
    PriceLineRead,
    PriceLinesCreate,
    PriceTableSummary,
    PriceTableWrite,
    WithdrawRequest,
)
from app.modules.pricing.service import PricingService
from app.modules.users.models import User
from app.shared.permissions import Permission
from app.shared.schemas import Page

ContractId = Annotated[uuid.UUID, Path(alias="contractId")]
TableId = Annotated[uuid.UUID, Path(alias="tableId")]
LineId = Annotated[uuid.UUID, Path(alias="lineId")]
ClauseId = Annotated[uuid.UUID, Path(alias="clauseId")]
FuelPriceId = Annotated[uuid.UUID, Path(alias="fuelPriceId")]
# Which prices (selling or buying) a user sees is checked per contract side in the service.
CanRead = Annotated[User, require_permission(Permission.CONTRACTS_READ)]
CanRegister = Annotated[User, require_permission(Permission.CONTRACTS_REGISTER)]
CanManageFuel = Annotated[User, require_permission(Permission.FUEL_PRICES_MANAGE)]

router = APIRouter(tags=["pricing"], route_class=DishkaRoute)


@router.get("/contracts/{contractId}/pricing")
async def get_contract_pricing(
    contract_id: ContractId, user: CanRead, service: FromDishka[PricingService]
) -> ContractPricing:
    return await service.contract_pricing(contract_id, user.permissions)


@router.get("/contracts/{contractId}/fuel-adjustment")
async def get_fuel_adjustment(
    contract_id: ContractId,
    params: Annotated[FuelAdjustmentParams, Query()],
    user: CanRead,
    service: FromDishka[PricingService],
) -> FuelAdjustment:
    return await service.fuel_adjustment(contract_id, params.on, user.permissions)


@router.post("/price-tables", status_code=status.HTTP_201_CREATED)
async def create_price_table(
    body: PriceTableWrite, user: CanRegister, service: FromDishka[PricingService]
) -> PriceTableSummary:
    return await service.add_table(body, user.id, user.permissions)


@router.post("/price-tables/{tableId}/withdraw", status_code=status.HTTP_204_NO_CONTENT)
async def withdraw_price_table(
    table_id: TableId,
    body: WithdrawRequest,
    user: CanRegister,
    service: FromDishka[PricingService],
) -> None:
    await service.withdraw_table(table_id, body, user.id, user.permissions)


@router.post("/price-tables/{tableId}/lines", status_code=status.HTTP_201_CREATED)
async def create_price_lines(
    table_id: TableId,
    body: PriceLinesCreate,
    user: CanRegister,
    service: FromDishka[PricingService],
) -> list[PriceLineRead]:
    return await service.add_lines(table_id, body, user.id, user.permissions)


@router.put("/price-lines/{lineId}")
async def correct_price_line(
    line_id: LineId,
    body: PriceLineCorrection,
    user: CanRegister,
    service: FromDishka[PricingService],
) -> PriceLineRead:
    return await service.correct_line(line_id, body, user.id, user.permissions)


@router.post("/price-lines/{lineId}/withdraw", status_code=status.HTTP_204_NO_CONTENT)
async def withdraw_price_line(
    line_id: LineId,
    body: WithdrawRequest,
    user: CanRegister,
    service: FromDishka[PricingService],
) -> None:
    await service.withdraw_line(line_id, body, user.id, user.permissions)


@router.post("/fuel-clauses", status_code=status.HTTP_201_CREATED)
async def create_fuel_clause(
    body: FuelClauseWrite, user: CanRegister, service: FromDishka[PricingService]
) -> FuelClauseRead:
    return await service.add_fuel_clause(body, user.id, user.permissions)


@router.post("/fuel-clauses/{clauseId}/withdraw", status_code=status.HTTP_204_NO_CONTENT)
async def withdraw_fuel_clause(
    clause_id: ClauseId,
    body: WithdrawRequest,
    user: CanRegister,
    service: FromDishka[PricingService],
) -> None:
    await service.withdraw_fuel_clause(clause_id, body, user.id, user.permissions)


@router.get("/fuel-prices")
async def list_fuel_prices(
    params: Annotated[FuelPriceFilter, Query()], _: CanRead, service: FromDishka[PricingService]
) -> Page[FuelPriceRead]:
    return await service.list_fuel_prices(params)


@router.post("/fuel-prices", status_code=status.HTTP_201_CREATED)
async def create_fuel_price(
    body: FuelPriceWrite, user: CanManageFuel, service: FromDishka[PricingService]
) -> FuelPriceRead:
    return await service.add_fuel_price(body, user.id)


@router.post("/fuel-prices/sync")
async def sync_fuel_prices(
    _: CanManageFuel, service: FromDishka[PricingService], source: FromDishka[FuelPriceSource]
) -> FuelPriceSyncReport:
    """Fetch the prices Petrolimex publishes now (the hourly job does the same)."""
    return await service.sync_fuel_prices(source)


@router.delete("/fuel-prices/{fuelPriceId}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fuel_price(
    fuel_price_id: FuelPriceId, _: CanManageFuel, service: FromDishka[PricingService]
) -> None:
    await service.delete_fuel_price(fuel_price_id)
