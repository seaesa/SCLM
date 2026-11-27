import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field

from app.modules.partners.models import ConflictKind
from app.shared.pagination import CursorParams, PageParams
from app.shared.schemas import Schema


class PartnerRole(StrEnum):
    CUSTOMER = "customer"
    SUPPLIER = "supplier"


class PartnerSummary(Schema):
    """What a list needs to name a partner."""

    id: uuid.UUID
    code: str
    name: str
    owner_id: uuid.UUID | None = None


class OwnerSummary(Schema):
    id: uuid.UUID
    name: str


class PartnerRead(Schema):
    id: uuid.UUID
    code: str
    name: str
    legal_name: str | None
    tax_code: str | None
    address: str | None
    email: str | None
    phone: str | None
    is_customer: bool
    is_supplier: bool
    is_active: bool
    can_order_before_contract: bool
    synced_at: datetime
    created_at: datetime
    owner: OwnerSummary | None = None


class PartnerFilter(PageParams):
    q: str | None = Field(default=None, min_length=2, max_length=100)
    role: PartnerRole | None = None
    owner_id: uuid.UUID | None = None
    # True: only partners nobody looks after yet.
    is_unassigned: bool | None = None


class AssignOwner(Schema):
    partner_ids: list[uuid.UUID] = Field(min_length=1, max_length=1000)
    # Null takes the partners back from whoever had them.
    owner_id: uuid.UUID | None


class PartnerConflictRead(Schema):
    id: uuid.UUID
    partner_id: uuid.UUID
    partner_code: str
    partner_name: str
    kind: ConflictKind
    detail: dict[str, Any]
    created_at: datetime
    resolved_at: datetime | None
    resolution_note: str | None


class PartnerConflictFilter(CursorParams):
    is_open: bool = True


class ResolveConflictRequest(Schema):
    note: str = Field(min_length=1, max_length=2000)


class SyncReport(Schema):
    source: str
    created: int
    updated: int
    unchanged: int
    conflicts_opened: int
    conflicts_closed: int
    conflicts_open: int
