"""The seed bundle: one folder, kept outside git, holding everything a fresh install needs.

<bundle>/seed.json        the manifest below; every path in it is relative to the bundle
<bundle>/users.json       [{"email", "fullName", "roles"}], never passwords
partner exports, scan folders and the checked archive file it points to
"""

from enum import StrEnum

from pydantic import EmailStr, Field

from app.shared.permissions import Role
from app.shared.schemas import Schema


class SeedStep(StrEnum):
    # In run order: each step needs the ones before it.
    USERS = "users"
    PARTNERS = "partners"
    FILES = "files"
    ARCHIVE = "archive"
    FUEL_PRICES = "fuel-prices"


class BySide(Schema):
    customers: list[str] = Field(default_factory=list)
    suppliers: list[str] = Field(default_factory=list)


class SeedManifest(Schema):
    version: int = 1
    users: str | None = None
    partners: BySide = Field(default_factory=BySide)
    files: BySide = Field(default_factory=BySide)
    archive: str | None = None
    # Recorded as the author of archive contracts; must be one of the seeded users.
    archive_author: EmailStr | None = None


class SeedUser(Schema):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    roles: list[Role] = Field(min_length=1)
