import uuid

from app.modules.archive.schemas import ArchiveImportReport, ArchiveSeed
from app.modules.archive.source import ArchivePartnerSource
from app.modules.contracts.service import ContractService
from app.modules.documents.models import DocumentSide
from app.modules.documents.service import DocumentService
from app.modules.partners.service import PartnerService


class ArchiveService:
    """Loads the archive seed. Safe to run again: dossiers are matched by key, contracts and
    their documents by file, so a re-run only adds what is new."""

    def __init__(
        self, partners: PartnerService, documents: DocumentService, contracts: ContractService
    ) -> None:
        self.partners = partners
        self.documents = documents
        self.contracts = contracts

    async def import_seed(self, seed: ArchiveSeed, actor_id: uuid.UUID) -> ArchiveImportReport:
        report = ArchiveImportReport()
        if seed.new_partners:
            report.partners_created = (await self.partners.sync(ArchivePartnerSource(seed))).created
        codes = {d.partner for d in seed.dossiers if d.partner}
        partner_ids = await self.partners.ids_by_code(codes)
        unknown = sorted(codes - partner_ids.keys())
        if unknown:
            raise ValueError(f"Partners not synced yet (run sync-partners): {unknown}")
        shas = {f.sha256 for d in seed.dossiers for f in d.files}
        file_ids = await self.documents.file_ids(shas)
        report.missing_files = sorted(shas - file_ids.keys())
        if report.missing_files:
            return report

        contract_of_file: dict[str, uuid.UUID] = {}
        for dossier in seed.dossiers:
            partner_id = partner_ids.get(dossier.partner) if dossier.partner else None
            set_id = await self.documents.archive_dossier(
                f"archive/{dossier.key}",
                DocumentSide(dossier.side),
                partner_id,
                [(f.path, file_ids[f.sha256]) for f in dossier.files],
            )
            report.dossiers += 1
            if partner_id is None:
                continue
            for contract in dossier.contracts:
                result = await self.contracts.import_archived(contract, set_id, file_ids, actor_id)
                contract_of_file[contract.document.sha256] = result.contract_id
                if result.is_new:
                    report.contracts_created += 1
                else:
                    report.contracts_existing += 1
                report.documents_added += result.documents_added
                report.rejected_facts += result.rejected_facts
        for dossier in seed.dossiers:
            for contract in dossier.contracts:
                previous = contract_of_file.get(contract.replaces or "")
                successor = contract_of_file.get(contract.document.sha256)
                if (
                    previous
                    and successor
                    and await self.contracts.mark_replaced(previous, successor)
                ):
                    report.replacements += 1
        return report
