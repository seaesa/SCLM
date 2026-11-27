import uuid
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.partners.models import ConflictKind, Partner
from app.modules.partners.repository import (
    ConflictRepository,
    ExternalRefRepository,
    PartnerRepository,
    detail_key,
)
from app.modules.partners.schemas import (
    AssignOwner,
    OwnerSummary,
    PartnerConflictFilter,
    PartnerConflictRead,
    PartnerFilter,
    PartnerRead,
    PartnerSummary,
    SyncReport,
)
from app.modules.partners.source import PartnerSource, SourcePartner
from app.modules.users.service import UserService
from app.shared.pagination import encode_cursor
from app.shared.permissions import Permission, has_permission
from app.shared.schemas import CursorPage, ErrorCode, Page

CLEARED_BY_SYNC = "Cleared by synchronization: the source no longer shows this problem."


def _values(record: SourcePartner) -> dict[str, Any]:
    return {
        "code": record.external_code,
        "name": record.name,
        "legal_name": record.legal_name,
        "tax_code": record.tax_code,
        "address": record.address,
        "email": record.email,
        "phone": record.phone,
        "is_customer": record.is_customer,
        "is_supplier": record.is_supplier,
        "is_active": record.is_active,
        "can_order_before_contract": record.can_order_before_contract,
    }


ConflictKey = tuple[uuid.UUID, str]


class PartnerService:
    """Public API of the partners module. Partners are read-only for users: they change only
    through `sync` from the source of record (ADR 0006)."""

    def __init__(
        self,
        session: AsyncSession,
        partners: PartnerRepository,
        refs: ExternalRefRepository,
        conflicts: ConflictRepository,
        users: UserService,
    ) -> None:
        self.session = session
        self.partners = partners
        self.refs = refs
        self.conflicts = conflicts
        self.users = users

    async def _reads(self, partners: Sequence[Partner]) -> list[PartnerRead]:
        names = await self.users.names({p.owner_id for p in partners if p.owner_id})
        return [
            PartnerRead.model_validate(p).model_copy(
                update={
                    "owner": OwnerSummary(id=p.owner_id, name=names[p.owner_id])
                    if p.owner_id in names
                    else None
                }
            )
            for p in partners
        ]

    async def read(self, partner_id: uuid.UUID) -> PartnerRead:
        return (await self._reads([await self.get(partner_id)]))[0]

    async def ids_owned(self, owner_id: uuid.UUID | None) -> Sequence[uuid.UUID]:
        """Partners this person looks after; `None` gives the partners nobody looks after."""
        return await self.partners.ids_owned(owner_id)

    async def owner_candidates(self) -> list[OwnerSummary]:
        """Who can be put in charge of partners: anyone who handles contracts."""
        users = await self.users.active_with(Permission.CONTRACTS_REGISTER)
        return [OwnerSummary(id=user.id, name=user.full_name) for user in users]

    async def assign_owner(self, body: AssignOwner) -> int:
        """Hand partners, and with them their contracts, to one accountant."""
        if body.owner_id is not None:
            owner = await self.users.get(body.owner_id)
            if (
                owner is None
                or not owner.is_active
                or not has_permission(owner.roles, Permission.CONTRACTS_REGISTER)
            ):
                raise ConflictError(
                    "The owner must be an active user who handles contracts",
                    code=ErrorCode.OWNER_CANNOT_HANDLE_CONTRACTS,
                    field="ownerId",
                )
        count = await self.partners.assign(body.partner_ids, body.owner_id)
        await self.session.commit()
        return count

    async def list(self, params: PartnerFilter) -> Page[PartnerRead]:
        rows, total = await self.partners.list_page(params)
        return Page[PartnerRead](
            items=await self._reads(rows),
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    async def ids_matching(self, q: str, limit: int = 500) -> Sequence[uuid.UUID]:
        """Partners whose code, name or tax code matches, for other modules' searches."""
        return await self.partners.ids_matching(q, limit)

    async def get(self, partner_id: uuid.UUID) -> Partner:
        partner = await self.partners.get(partner_id)
        if partner is None:
            raise NotFoundError("Partner not found")
        return partner

    async def summaries(self, partner_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, PartnerSummary]:
        rows = await self.partners.list(Partner.id.in_(partner_ids)) if partner_ids else []
        return {p.id: PartnerSummary.model_validate(p) for p in rows}

    async def list_conflicts(
        self, params: PartnerConflictFilter
    ) -> CursorPage[PartnerConflictRead]:
        rows = await self.conflicts.list_page(params)
        items = [
            PartnerConflictRead(
                id=c.id,
                partner_id=c.partner_id,
                partner_code=p.code,
                partner_name=p.name,
                kind=c.kind,
                detail=c.detail,
                created_at=c.created_at,
                resolved_at=c.resolved_at,
                resolution_note=c.resolution_note,
            )
            for c, p in rows
        ]
        return CursorPage[PartnerConflictRead].create(
            items, params.limit, lambda c: encode_cursor(c.created_at, c.id)
        )

    async def resolve_conflict(self, conflict_id: uuid.UUID, user_id: uuid.UUID, note: str) -> None:
        """An administrator accepts the situation (e.g. two branches sharing a tax code). The
        same unchanged problem is not reopened by later syncs; a different one is."""
        conflict = await self.conflicts.get(conflict_id)
        if conflict is None:
            raise NotFoundError("Conflict not found")
        if conflict.resolved_at is not None:
            raise ConflictError("Conflict already resolved")
        await self.conflicts.update(
            conflict, resolved_at=datetime.now(UTC), resolved_by_id=user_id, resolution_note=note
        )
        await self.session.commit()

    async def ids_by_code(self, codes: Iterable[str]) -> dict[str, uuid.UUID]:
        wanted = list(set(codes))
        if not wanted:
            return {}
        return {p.code: p.id for p in await self.partners.list(Partner.code.in_(wanted))}

    async def sync(self, source: PartnerSource) -> SyncReport:
        """Bring the catalogue in line with `source` in one transaction: create and update
        partners, then recompute conflicts. Nothing is merged or deleted."""
        records = source.fetch()
        now = datetime.now(UTC)
        refs = await self.refs.for_source(source.name)
        known = {
            p.id: p
            for p in await self.partners.list(
                Partner.id.in_([ref.partner_id for ref in refs.values()])
            )
        }
        created = updated = unchanged = 0
        desired: dict[ConflictKey, dict[str, Any]] = {}

        for record in records:
            values = _values(record)
            ref = refs.get(record.external_code)
            if ref is None:
                partner = await self.partners.create(**values, synced_at=now)
                await self.refs.create(
                    partner_id=partner.id,
                    source=source.name,
                    external_code=record.external_code,
                    payload=record.raw,
                    synced_at=now,
                )
                created += 1
            else:
                partner = known[ref.partner_id]
                if any(getattr(partner, k) != v for k, v in values.items()):
                    updated += 1
                else:
                    unchanged += 1
                await self.partners.update(partner, **values, synced_at=now)
                await self.refs.update(ref, payload=record.raw, synced_at=now)
            if record.mismatches:
                desired[(partner.id, ConflictKind.SOURCE_MISMATCH)] = {
                    "source": source.name,
                    "fields": record.mismatches,
                }

        listed = {record.external_code for record in records}
        for code, ref in refs.items():
            if code not in listed:
                desired[(ref.partner_id, ConflictKind.MISSING_FROM_SOURCE)] = {
                    "source": source.name,
                    "externalCode": code,
                }

        for tax_code, group in (await self.partners.by_tax_code()).items():
            codes = [p.code for p in group]
            for partner in group:
                desired[(partner.id, ConflictKind.DUPLICATE_TAX_CODE)] = {
                    "taxCode": tax_code,
                    "partnerCodes": codes,
                }

        opened, closed = await self._reconcile(source.name, desired, now)
        await self.session.commit()
        return SyncReport(
            source=source.name,
            created=created,
            updated=updated,
            unchanged=unchanged,
            conflicts_opened=opened,
            conflicts_closed=closed,
            conflicts_open=await self.conflicts.count_open(),
        )

    async def _reconcile(
        self, source: str, desired: dict[ConflictKey, dict[str, Any]], now: datetime
    ) -> tuple[int, int]:
        open_ = await self.conflicts.open_conflicts()
        acknowledged = await self.conflicts.acknowledged()
        opened = closed = 0
        for (partner_id, kind), detail in desired.items():
            current = open_.get((partner_id, kind))
            if current is not None:
                if current.detail != detail:
                    await self.conflicts.update(current, detail=detail)
            elif (partner_id, kind, detail_key(detail)) not in acknowledged:
                await self.conflicts.create(partner_id=partner_id, kind=kind, detail=detail)
                opened += 1
        for key, conflict in open_.items():
            # Tax-code duplicates span every source; the other kinds belong to one source.
            ours = conflict.kind == ConflictKind.DUPLICATE_TAX_CODE or (
                conflict.detail.get("source") == source
            )
            if key not in desired and ours:
                await self.conflicts.update(
                    conflict, resolved_at=now, resolution_note=CLEARED_BY_SYNC
                )
                closed += 1
        return opened, closed
