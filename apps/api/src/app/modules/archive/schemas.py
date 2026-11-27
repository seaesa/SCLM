"""The archive seed: what the scanned contract archive says, read once and checked (see
docs/business/13_Seed_kho_hop_dong.md). Files are named by their SHA-256; the bytes come from
`ingest-documents`."""

from pydantic import Field

from app.modules.contracts.schemas import ArchivedContract
from app.modules.partners.schemas import PartnerRole
from app.shared.schemas import Schema


class SeedPartner(Schema):
    """A counterparty printed on a contract but missing from the source of record."""

    code: str
    name: str
    tax_code: str | None = None
    side: PartnerRole


class SeedFile(Schema):
    sha256: str
    path: str


class SeedDossier(Schema):
    """Every file of one partner on one side, wherever it was filed in the archive."""

    key: str
    partner: str | None
    side: PartnerRole
    files: list[SeedFile]
    contracts: list[ArchivedContract] = Field(default_factory=list)


class ArchiveSeed(Schema):
    version: int
    new_partners: list[SeedPartner] = Field(default_factory=list)
    dossiers: list[SeedDossier]


class ArchiveImportReport(Schema):
    partners_created: int = 0
    dossiers: int = 0
    contracts_created: int = 0
    contracts_existing: int = 0
    documents_added: int = 0
    replacements: int = 0
    # Files the seed names that are not stored yet: run `ingest-documents` first.
    missing_files: list[str] = Field(default_factory=list)
    # Facts the contract fields refused: "<sha256 prefix> <key>=<value>".
    rejected_facts: list[str] = Field(default_factory=list)
