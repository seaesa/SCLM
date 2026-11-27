import uuid
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Path, Query, status

from app.modules.auth.dependencies import require_permission
from app.modules.partners.schemas import (
    AssignOwner,
    OwnerSummary,
    PartnerConflictFilter,
    PartnerConflictRead,
    PartnerFilter,
    PartnerRead,
    ResolveConflictRequest,
)
from app.modules.partners.service import PartnerService
from app.modules.users.models import User
from app.shared.permissions import Permission
from app.shared.schemas import CursorPage, Page

PartnerId = Annotated[uuid.UUID, Path(alias="partnerId")]
ConflictId = Annotated[uuid.UUID, Path(alias="conflictId")]
CanRead = Annotated[User, require_permission(Permission.PARTNERS_READ)]
CanSync = Annotated[User, require_permission(Permission.PARTNERS_SYNC)]
CanAssign = Annotated[User, require_permission(Permission.PARTNERS_ASSIGN)]

router = APIRouter(tags=["partners"], route_class=DishkaRoute)


@router.get("/partners")
async def list_partners(
    params: Annotated[PartnerFilter, Query()], _: CanRead, service: FromDishka[PartnerService]
) -> Page[PartnerRead]:
    return await service.list(params)


@router.get("/partners/owner-candidates")
async def list_partner_owner_candidates(
    _: CanAssign, service: FromDishka[PartnerService]
) -> list[OwnerSummary]:
    return await service.owner_candidates()


@router.get("/partners/{partnerId}")
async def get_partner(
    partner_id: PartnerId, _: CanRead, service: FromDishka[PartnerService]
) -> PartnerRead:
    return await service.read(partner_id)


@router.put("/partners/owner", status_code=status.HTTP_204_NO_CONTENT)
async def assign_partner_owner(
    body: AssignOwner, _: CanAssign, service: FromDishka[PartnerService]
) -> None:
    await service.assign_owner(body)


@router.get("/partner-conflicts")
async def list_partner_conflicts(
    params: Annotated[PartnerConflictFilter, Query()],
    _: CanSync,
    service: FromDishka[PartnerService],
) -> CursorPage[PartnerConflictRead]:
    return await service.list_conflicts(params)


@router.post("/partner-conflicts/{conflictId}/resolve", status_code=status.HTTP_204_NO_CONTENT)
async def resolve_partner_conflict(
    conflict_id: ConflictId,
    data: ResolveConflictRequest,
    user: CanSync,
    service: FromDishka[PartnerService],
) -> None:
    await service.resolve_conflict(conflict_id, user.id, data.note)
