import uuid
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Path, Query, status

from app.modules.auth.dependencies import CurrentUser, require_permission
from app.modules.auth.schemas import DeleteAccountRequest
from app.modules.auth.service import AuthService
from app.modules.users.models import User
from app.modules.users.schemas import (
    UserAdminUpdate,
    UserFilter,
    UserInvite,
    UserRead,
    UserUpdate,
)
from app.modules.users.service import UserService
from app.shared.locale import RequestLocale
from app.shared.permissions import Permission
from app.shared.schemas import Page

UserId = Annotated[uuid.UUID, Path(alias="userId")]
CanManage = Annotated[User, require_permission(Permission.USERS_MANAGE)]

router = APIRouter(prefix="/users", tags=["users"], route_class=DishkaRoute)


@router.get("")
async def list_users(
    params: Annotated[UserFilter, Query()],
    _: Annotated[User, require_permission(Permission.USERS_READ)],
    service: FromDishka[UserService],
) -> Page[UserRead]:
    return await service.list(params)


@router.get("/me")
async def get_me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)


@router.patch("/me")
async def update_me(
    data: UserUpdate, user: CurrentUser, service: FromDishka[UserService]
) -> UserRead:
    return UserRead.model_validate(await service.update(user, data))


@router.post("/me/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    data: DeleteAccountRequest, user: CurrentUser, auth: FromDishka[AuthService]
) -> None:
    """Delete the account and everything it owns; the password is the confirmation."""
    await auth.delete_account(user, data.password)


@router.post("", status_code=status.HTTP_201_CREATED)
async def invite_user(
    data: UserInvite,
    _: CanManage,
    service: FromDishka[UserService],
    auth: FromDishka[AuthService],
    locale: RequestLocale,
) -> UserRead:
    """Open an account and email the person a link to set their password."""
    user = await service.invite(data)
    await auth.forgot_password(user.email, locale)
    return UserRead.model_validate(user)


@router.patch("/{userId}")
async def administer_user(
    user_id: UserId, data: UserAdminUpdate, admin: CanManage, service: FromDishka[UserService]
) -> UserRead:
    return UserRead.model_validate(await service.administer(user_id, data, admin))


@router.post("/{userId}/password-email", status_code=status.HTTP_204_NO_CONTENT)
async def send_user_password_email(
    user_id: UserId,
    _: CanManage,
    service: FromDishka[UserService],
    auth: FromDishka[AuthService],
    locale: RequestLocale,
) -> None:
    """Send the set-password link again (lost email, forgotten password)."""
    user = await service.get(user_id)
    if user is not None:
        await auth.forgot_password(user.email, locale)
