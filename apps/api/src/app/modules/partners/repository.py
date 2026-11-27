import json
import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import ColumnElement, func, select, tuple_, update

from app.modules.partners.models import Partner, PartnerConflict, PartnerExternalRef
from app.modules.partners.schemas import PartnerConflictFilter, PartnerFilter, PartnerRole
from app.shared.repository import BaseRepository


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class PartnerRepository(BaseRepository[Partner]):
    model = Partner

    async def list_page(self, params: PartnerFilter) -> tuple[Sequence[Partner], int]:
        """By code, so a person paging through finds a partner where they expect it."""
        filters = self._filters(params)
        return await self.page(
            self._select(*filters), [Partner.code, Partner.id], params.offset, params.page_size
        )

    async def ids_matching(self, q: str, limit: int) -> Sequence[uuid.UUID]:
        filters = self._filters(PartnerFilter(q=q))
        rows = await self.session.scalars(select(Partner.id).where(*filters).limit(limit))
        return rows.all()

    @staticmethod
    def _filters(params: PartnerFilter) -> list[ColumnElement[bool]]:
        filters: list[ColumnElement[bool]] = []
        if params.role == PartnerRole.CUSTOMER:
            filters.append(Partner.is_customer.is_(True))
        elif params.role == PartnerRole.SUPPLIER:
            filters.append(Partner.is_supplier.is_(True))
        if params.owner_id is not None:
            filters.append(Partner.owner_id == params.owner_id)
        if params.is_unassigned:
            filters.append(Partner.owner_id.is_(None))
        if params.q:
            haystack = func.lower(
                Partner.code + " " + Partner.name + " " + func.coalesce(Partner.legal_name, "")
            )
            needle = f"%{_escape_like(params.q.lower())}%"
            filters.append(haystack.like(needle, escape="\\") | (Partner.tax_code == params.q))
        return filters

    async def ids_owned(self, owner_id: uuid.UUID | None) -> Sequence[uuid.UUID]:
        condition = Partner.owner_id.is_(None) if owner_id is None else Partner.owner_id == owner_id
        return (await self.session.scalars(select(Partner.id).where(condition))).all()

    async def assign(self, partner_ids: Sequence[uuid.UUID], owner_id: uuid.UUID | None) -> int:
        result = await self.session.execute(
            update(Partner).where(Partner.id.in_(partner_ids)).values(owner_id=owner_id)
        )
        return int(getattr(result, "rowcount", 0) or 0)

    async def by_tax_code(self) -> dict[str, list[Partner]]:
        """Partners grouped by tax code, only for codes shared by more than one partner."""
        shared = (
            select(Partner.tax_code)
            .where(Partner.tax_code.is_not(None))
            .group_by(Partner.tax_code)
            .having(func.count() > 1)
        )
        rows = await self.list(Partner.tax_code.in_(shared), order_by=[Partner.code])
        groups: dict[str, list[Partner]] = {}
        for partner in rows:
            groups.setdefault(partner.tax_code or "", []).append(partner)
        return groups


class ExternalRefRepository(BaseRepository[PartnerExternalRef]):
    model = PartnerExternalRef

    async def for_source(self, source: str) -> dict[str, PartnerExternalRef]:
        rows = await self.list(PartnerExternalRef.source == source)
        return {ref.external_code: ref for ref in rows}


class ConflictRepository(BaseRepository[PartnerConflict]):
    model = PartnerConflict

    async def open_conflicts(self) -> dict[tuple[uuid.UUID, str], PartnerConflict]:
        rows = await self.list(PartnerConflict.resolved_at.is_(None))
        return {(c.partner_id, c.kind): c for c in rows}

    async def acknowledged(self) -> set[tuple[uuid.UUID, str, str]]:
        """Conflicts an administrator closed by hand, as (partner, kind, detail) keys, so the
        same unchanged problem is not reopened by the next sync."""
        stmt = select(
            PartnerConflict.partner_id, PartnerConflict.kind, PartnerConflict.detail
        ).where(PartnerConflict.resolved_by_id.is_not(None))
        rows = (await self.session.execute(stmt)).all()
        return {(row[0], row[1], detail_key(row[2])) for row in rows}

    async def count_open(self) -> int:
        stmt = select(func.count()).where(PartnerConflict.resolved_at.is_(None))
        return int((await self.session.execute(stmt)).scalar_one())

    async def list_page(
        self, params: PartnerConflictFilter
    ) -> Sequence[tuple[PartnerConflict, Partner]]:
        stmt = select(PartnerConflict, Partner).join(
            Partner, Partner.id == PartnerConflict.partner_id
        )
        if params.is_open:
            stmt = stmt.where(PartnerConflict.resolved_at.is_(None))
        else:
            stmt = stmt.where(PartnerConflict.resolved_at.is_not(None))
        if params.after:
            stmt = stmt.where(
                tuple_(PartnerConflict.created_at, PartnerConflict.id) < tuple_(*params.after)
            )
        stmt = stmt.order_by(PartnerConflict.created_at.desc(), PartnerConflict.id.desc()).limit(
            params.limit + 1
        )
        return [(row[0], row[1]) for row in (await self.session.execute(stmt)).all()]


def detail_key(detail: dict[str, Any]) -> str:
    return json.dumps(detail, sort_keys=True, ensure_ascii=False)
