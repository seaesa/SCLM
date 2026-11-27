"""Partners for tests, created through the real sync path (ADR 0006)."""

from collections.abc import Sequence

from dishka import AsyncContainer

from app.modules.partners.schemas import SyncReport
from app.modules.partners.service import PartnerService
from app.modules.partners.source import SourcePartner


def partner(code: str, name: str, tax_code: str | None = None, **kw: object) -> SourcePartner:
    values: dict[str, object] = {
        "external_code": code,
        "name": name,
        "legal_name": None,
        "tax_code": tax_code,
        "address": None,
        "email": None,
        "phone": None,
        "is_customer": True,
        "is_supplier": False,
        "is_active": True,
        "can_order_before_contract": False,
        "raw": {"code": code},
    }
    values.update(kw)
    return SourcePartner(**values)  # type: ignore[arg-type]


class FakeSource:
    name = "test"

    def __init__(self, *records: SourcePartner) -> None:
        self.records: Sequence[SourcePartner] = records

    def fetch(self) -> Sequence[SourcePartner]:
        return self.records


async def sync(container: AsyncContainer, source: FakeSource) -> SyncReport:
    async with container() as request:
        return await (await request.get(PartnerService)).sync(source)
