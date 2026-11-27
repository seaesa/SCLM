from collections.abc import Sequence

from app.modules.archive.schemas import ArchiveSeed
from app.modules.partners.schemas import PartnerRole
from app.modules.partners.source import SourcePartner


class ArchivePartnerSource:
    """Partners known only from the archive's own papers, synced like any other source so they
    stay read-only and show up as conflicts once the source of record lists them (ADR 0006)."""

    name = "archive"

    def __init__(self, seed: ArchiveSeed) -> None:
        self.seed = seed

    def fetch(self) -> Sequence[SourcePartner]:
        return [
            SourcePartner(
                external_code=p.code,
                name=p.name,
                legal_name=p.name,
                tax_code=p.tax_code,
                address=None,
                email=None,
                phone=None,
                is_customer=p.side == PartnerRole.CUSTOMER,
                is_supplier=p.side == PartnerRole.SUPPLIER,
                is_active=True,
                can_order_before_contract=False,
                raw=p.model_dump(mode="json"),
            )
            for p in self.seed.new_partners
        ]
