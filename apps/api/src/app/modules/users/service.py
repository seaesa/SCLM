import secrets
import uuid
from collections.abc import Iterable
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.security import hash_password_async
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import (
    UserAdminUpdate,
    UserCreate,
    UserFilter,
    UserInvite,
    UserRead,
    UserUpdate,
)
from app.shared.permissions import Permission, Role, permissions_for
from app.shared.schemas import ErrorCode, Page


class UserService:
    """Public API of the users module. Other modules depend on this, never on the repository."""

    def __init__(self, session: AsyncSession, users: UserRepository) -> None:
        self.session = session
        self.users = users

    async def get(self, user_id: uuid.UUID) -> User | None:
        return await self.users.get(user_id)

    async def names(self, user_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, str]:
        """Display names for a history trail; unknown ids are simply absent."""
        ids = list(set(user_ids))
        if not ids:
            return {}
        return {u.id: u.full_name for u in await self.users.list(User.id.in_(ids))}

    async def active_with(self, permission: Permission) -> list[User]:
        """Active users whose roles grant `permission`, by name."""
        return [
            user for user in await self.users.active() if permission in permissions_for(user.roles)
        ]

    async def get_by_email(self, email: str) -> User | None:
        return await self.users.get_by_email(email)

    async def list(self, params: UserFilter) -> Page[UserRead]:
        rows, total = await self.users.list_page(params)
        return Page[UserRead](
            items=[UserRead.model_validate(user) for user in rows],
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    async def invite(self, data: UserInvite) -> User:
        """Open an account with an unusable random password; the caller emails a set-password
        link, so an administrator never knows anyone's password."""
        user = await self.create(
            UserCreate(
                email=data.email, full_name=data.full_name, password=secrets.token_urlsafe(32)
            )
        )
        user = await self.users.update(
            user, roles=sorted(set(data.roles)), email_verified_at=datetime.now(UTC)
        )
        await self.session.commit()
        return user

    async def administer(self, user_id: uuid.UUID, data: UserAdminUpdate, admin: User) -> User:
        user = await self.users.get(user_id)
        if user is None:
            raise NotFoundError("User not found")
        changes = data.model_dump(exclude_unset=True)
        if "roles" in changes:
            changes["roles"] = sorted(set(changes["roles"]))
        if user.id == admin.id:
            # Locking yourself out leaves nobody to undo it.
            keeps_access = changes.get("is_active", True) and Permission.USERS_MANAGE in (
                permissions_for(changes.get("roles", user.roles))
            )
            if not keeps_access:
                raise ForbiddenError(
                    "You cannot remove your own access", code=ErrorCode.OWN_ACCESS_REQUIRED
                )
        if changes.get("is_active") is False or (
            "roles" in changes and changes["roles"] != user.roles
        ):
            # Tokens carry the version: a disabled person or a narrowed role takes effect now.
            changes["token_version"] = user.token_version + 1
        user = await self.users.update(user, **changes)
        await self.session.commit()
        return user

    async def set_roles(self, user: User, roles: Iterable[Role]) -> User:
        await self.users.update(user, roles=sorted(set(roles)))
        await self.session.commit()
        return user

    async def create(self, data: UserCreate) -> User:
        if await self.users.get_by_email(data.email):
            raise ConflictError(
                "Email already registered", code=ErrorCode.EMAIL_TAKEN, field="email"
            )
        try:
            user = await self.users.create(
                email=data.email.lower(),
                full_name=data.full_name,
                hashed_password=await hash_password_async(data.password),
            )
            await self.session.commit()
        except IntegrityError:
            # Another request committed the same email between the check and the insert.
            await self.session.rollback()
            raise ConflictError(
                "Email already registered", code=ErrorCode.EMAIL_TAKEN, field="email"
            ) from None
        return user

    async def update(self, user: User, data: UserUpdate) -> User:
        user = await self.users.update(user, **data.model_dump(exclude_unset=True))
        await self.session.commit()
        return user

    async def mark_verified(self, user: User) -> User:
        user = await self.users.update(user, email_verified_at=datetime.now(UTC))
        await self.session.commit()
        return user

    async def set_password(self, user: User, password: str) -> User:
        """Replace the password and invalidate every token issued so far."""
        user = await self.users.update(
            user,
            hashed_password=await hash_password_async(password),
            token_version=user.token_version + 1,
        )
        await self.session.commit()
        return user

    async def delete(self, user: User) -> None:
        await self.users.delete(user)
        await self.session.commit()
