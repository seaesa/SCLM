import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.shared.pagination import PageParams
from app.shared.permissions import Permission, Role
from app.shared.schemas import Schema, reject_null


class UserRead(Schema):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    is_active: bool
    email_verified: bool
    roles: list[Role]
    permissions: list[Permission]
    created_at: datetime


class UserCreate(Schema):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(Schema):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)

    _reject_null = reject_null("full_name")


class UserFilter(PageParams):
    q: str | None = Field(default=None, min_length=2, max_length=100)
    role: Role | None = None
    is_active: bool | None = None


class UserInvite(Schema):
    """An account an administrator opens; the person sets their own password from the email."""

    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    roles: list[Role] = Field(min_length=1)


class UserAdminUpdate(Schema):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    roles: list[Role] | None = None
    is_active: bool | None = None

    _reject_null = reject_null("full_name", "roles", "is_active")
