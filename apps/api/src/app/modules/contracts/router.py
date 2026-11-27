import uuid
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Form, Path, Query, Response, UploadFile, status

from app.modules.auth.dependencies import require_permission
from app.modules.contracts.export import instruments_workbook
from app.modules.contracts.models import ContractCategory
from app.modules.contracts.schemas import (
    ContractCreate,
    ContractDetail,
    ContractFilter,
    ContractRead,
    FactsWrite,
    FieldSpecRead,
    InstrumentCreate,
    InstrumentFilter,
    InstrumentListItem,
    InstrumentRead,
    ReviewDecision,
    ReviewSubmit,
    SigningWrite,
)
from app.modules.contracts.service import ContractService
from app.modules.partners.schemas import PartnerRole
from app.modules.users.models import User
from app.shared.permissions import Permission
from app.shared.schemas import Page

ContractId = Annotated[uuid.UUID, Path(alias="contractId")]
InstrumentId = Annotated[uuid.UUID, Path(alias="instrumentId")]
FileId = Annotated[uuid.UUID, Path(alias="fileId")]
CanRead = Annotated[User, require_permission(Permission.CONTRACTS_READ)]
CanRegister = Annotated[User, require_permission(Permission.CONTRACTS_REGISTER)]
CanApprove = Annotated[User, require_permission(Permission.CONTRACTS_APPROVE)]

router = APIRouter(tags=["contracts"], route_class=DishkaRoute)


@router.get("/contract-fields")
async def list_contract_fields(_: CanRead) -> list[FieldSpecRead]:
    return ContractService.field_specs()


@router.get("/contracts")
async def list_contracts(
    params: Annotated[ContractFilter, Query()], _: CanRead, service: FromDishka[ContractService]
) -> Page[ContractRead]:
    return await service.list(params)


@router.get("/contract-instruments")
async def list_contract_instruments(
    params: Annotated[InstrumentFilter, Query()], _: CanRead, service: FromDishka[ContractService]
) -> Page[InstrumentListItem]:
    return await service.list_instruments(params)


_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get(
    "/contract-instruments/export",
    response_class=Response,
    responses={200: {"content": {_XLSX: {}}}},
)
async def export_contract_instruments(
    params: Annotated[InstrumentFilter, Query()], _: CanRead, service: FromDishka[ContractService]
) -> Response:
    """Every document matching the filters (paging ignored) as an Excel file."""
    items = await service.all_instruments(params)
    return Response(
        instruments_workbook(items),
        media_type=_XLSX,
        headers={"Content-Disposition": 'attachment; filename="phu-luc.xlsx"'},
    )


@router.post("/contracts", status_code=status.HTTP_201_CREATED)
async def create_contract(
    category: Annotated[ContractCategory, Form()],
    partner_id: Annotated[uuid.UUID, Form(alias="partnerId")],
    file: UploadFile,
    user: CanRegister,
    service: FromDishka[ContractService],
    side: Annotated[PartnerRole | None, Form()] = None,
    needs_approval: Annotated[bool, Form(alias="needsApproval")] = False,
    replaces_id: Annotated[uuid.UUID | None, Form(alias="replacesId")] = None,
) -> ContractDetail:
    """A contract and its contract document, created together from the uploaded file."""
    body = ContractCreate(
        category=category,
        partner_id=partner_id,
        side=side,
        needs_approval=needs_approval,
        replaces_id=replaces_id,
    )
    return await service.create(body, file.filename or "contract.pdf", await file.read(), user.id)


@router.get("/contracts/{contractId}")
async def get_contract(
    contract_id: ContractId, _: CanRead, service: FromDishka[ContractService]
) -> ContractDetail:
    return await service.get(contract_id)


@router.post("/contracts/{contractId}/instruments", status_code=status.HTTP_201_CREATED)
async def add_contract_instrument(
    contract_id: ContractId,
    body: InstrumentCreate,
    user: CanRegister,
    service: FromDishka[ContractService],
) -> ContractDetail:
    return await service.add_instrument(contract_id, body, user.id)


@router.post("/contract-instruments/{instrumentId}/submit")
async def submit_contract_instrument(
    instrument_id: InstrumentId,
    body: ReviewSubmit,
    user: CanRegister,
    service: FromDishka[ContractService],
) -> ContractDetail:
    return await service.submit(instrument_id, body, user.id)


@router.post("/contract-instruments/{instrumentId}/approve")
async def approve_contract_instrument(
    instrument_id: InstrumentId,
    body: ReviewDecision,
    user: CanApprove,
    service: FromDishka[ContractService],
) -> ContractDetail:
    return await service.approve(instrument_id, body, user.id)


@router.post("/contract-instruments/{instrumentId}/reject")
async def reject_contract_instrument(
    instrument_id: InstrumentId,
    body: ReviewDecision,
    user: CanApprove,
    service: FromDishka[ContractService],
) -> ContractDetail:
    return await service.reject(instrument_id, body, user.id)


@router.put("/contract-instruments/{instrumentId}/signing")
async def set_contract_instrument_signing(
    instrument_id: InstrumentId,
    body: SigningWrite,
    user: CanRegister,
    service: FromDishka[ContractService],
) -> ContractDetail:
    return await service.set_signing(instrument_id, body, user.id)


@router.put("/contract-instruments/{instrumentId}/facts")
async def write_contract_facts(
    instrument_id: InstrumentId,
    body: FactsWrite,
    user: CanRegister,
    service: FromDishka[ContractService],
) -> InstrumentRead:
    return await service.write_facts(instrument_id, body, user.id)


@router.delete("/contracts/{contractId}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contract(
    contract_id: ContractId, _: CanRegister, service: FromDishka[ContractService]
) -> None:
    await service.delete(contract_id)


@router.delete("/contracts/{contractId}/files/{fileId}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_contract_file(
    contract_id: ContractId,
    file_id: FileId,
    _: CanRegister,
    service: FromDishka[ContractService],
) -> None:
    await service.remove_file(contract_id, file_id)


@router.delete("/contract-instruments/{instrumentId}")
async def delete_contract_instrument(
    instrument_id: InstrumentId, user: CanRegister, service: FromDishka[ContractService]
) -> ContractDetail:
    return await service.delete_instrument(instrument_id, user.id)
