from collections.abc import Sequence

from sqlalchemy import ColumnElement, func

from app.modules.users.models import User
from app.modules.users.schemas import UserFilter
from app.shared.repository import BaseRepository


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        return await self.find_one(User.email == email.lower())

    async def active(self) -> Sequence[User]:
        return await self.list(User.is_active.is_(True), order_by=[User.full_name, User.id])

    async def list_page(self, params: UserFilter) -> tuple[Sequence[User], int]:
        filters: list[ColumnElement[bool]] = []
        if params.q:
            needle = f"%{_escape_like(params.q.lower())}%"
            filters.append(func.lower(User.full_name + " " + User.email).like(needle, escape="\\"))
        if params.role is not None:
            filters.append(User.roles.contains([params.role]))
        if params.is_active is not None:
            filters.append(User.is_active.is_(params.is_active))
        return await self.page(
            self._select(*filters), [User.full_name, User.id], params.offset, params.page_size
        )
