from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter

from app.modules.auth.dependencies import require_permission
from app.modules.overview.schemas import Overview
from app.modules.overview.service import OverviewService
from app.modules.users.models import User
from app.shared.clock import business_today
from app.shared.permissions import Permission

CanRead = Annotated[User, require_permission(Permission.CONTRACTS_READ)]

router = APIRouter(prefix="/overview", tags=["overview"], route_class=DishkaRoute)


@router.get("")
async def get_overview(_: CanRead, service: FromDishka[OverviewService]) -> Overview:
    return await service.overview(business_today())
