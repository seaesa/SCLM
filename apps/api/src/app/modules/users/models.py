from datetime import datetime

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.shared.permissions import Permission, Role, permissions_for


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
    # A person can hold several jobs (sales who also verifies scans); no role means no access.
    roles: Mapped[list[Role]] = mapped_column(ARRAY(String(32)), default=list, server_default="{}")
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    # Bumped on password change/reset; access tokens carry it so old ones stop working.
    token_version: Mapped[int] = mapped_column(default=0, server_default="0")

    @property
    def email_verified(self) -> bool:
        return self.email_verified_at is not None

    @property
    def permissions(self) -> frozenset[Permission]:
        return permissions_for(self.roles)


# Uniqueness ignores case: `Jane@Example.com` and `jane@example.com` are the same account.
Index("uq_users_email_lower", func.lower(User.email), unique=True)
