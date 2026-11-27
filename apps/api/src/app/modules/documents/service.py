import asyncio
import uuid
from collections.abc import Iterable, Sequence
from pathlib import PurePosixPath

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.core.storage import ObjectStorage
from app.modules.documents.files import DiskFile
from app.modules.documents.models import DocumentFile, DocumentSet, DocumentSide
from app.modules.documents.repository import (
    DocumentFileRepository,
    DocumentSetFileRepository,
    DocumentSetRepository,
)
from app.modules.documents.schemas import (
    DocumentFileRead,
    DocumentSetDetail,
    DownloadUrl,
    LocatedFile,
    StoreReport,
)
from app.modules.partners.service import PartnerService
from app.shared.schemas import ErrorCode


class DocumentService:
    def __init__(
        self,
        session: AsyncSession,
        storage: ObjectStorage,
        files: DocumentFileRepository,
        sets: DocumentSetRepository,
        set_files: DocumentSetFileRepository,
        partners: PartnerService,
        settings: Settings,
    ) -> None:
        self.settings = settings
        self.session = session
        self.storage = storage
        self.files = files
        self.sets = sets
        self.set_files = set_files
        self.partners = partners

    async def store(self, item: DiskFile, report: StoreReport) -> None:
        """Keep the bytes of one scanned file; the same bytes filed twice are stored once and
        nothing stored is ever removed (ADR 0005). Where the file belongs is decided by the
        archive seed, not here."""
        data = await asyncio.to_thread(item.absolute.read_bytes)
        _, is_new = await self._store(data, item.content_type)
        await self.session.commit()
        if is_new:
            report.files_stored += 1
        else:
            report.files_already_stored += 1

    async def file_ids(self, sha256s: Iterable[str]) -> dict[str, uuid.UUID]:
        """Stored files among `sha256s`, by hash."""
        wanted = list(set(sha256s))
        if not wanted:
            return {}
        return {f.sha256: f.id for f in await self.files.list(DocumentFile.sha256.in_(wanted))}

    async def locate(self, term: str, limit: int = 50) -> list[LocatedFile]:
        """Find stored files by part of the name they were filed under, or by hash prefix."""
        return [
            LocatedFile(
                path=link.path,
                sha256=file.sha256,
                storage_key=file.storage_key,
                size=file.size,
                dossier=dossier.source_path,
            )
            for link, file, dossier in await self.set_files.matching(term, limit)
        ]

    async def archive_dossier(
        self,
        source_path: str,
        side: DocumentSide,
        partner_id: uuid.UUID | None,
        files: Sequence[tuple[str, uuid.UUID]],
    ) -> uuid.UUID:
        """One partner's archive files gathered from wherever they were filed, already stored.
        Re-running adds missing links only."""
        dossier = await self.sets.by_source_path(source_path)
        if dossier is None:
            dossier = await self.sets.create(
                source_path=source_path, side=side, file_count=0, partner_id=partner_id
            )
        elif dossier.partner_id is None and partner_id is not None:
            await self.sets.update(dossier, partner_id=partner_id)
        linked = {link.path for link, _ in await self.set_files.files_of(dossier.id)}
        for path, file_id in files:
            if path not in linked:
                linked.add(path)
                await self.set_files.create(set_id=dossier.id, file_id=file_id, path=path)
        await self.sets.update(dossier, file_count=len(linked))
        await self.session.commit()
        return dossier.id

    async def _store(self, data: bytes, content_type: str) -> tuple[DocumentFile, bool]:
        obj = await self.storage.put(data, content_type)
        file = await self.files.by_sha256(obj.sha256)
        if file is not None:
            return file, False
        file = await self.files.create(
            sha256=obj.sha256, storage_key=obj.key, size=obj.size, content_type=content_type
        )
        return file, True

    async def create_set(self, side: DocumentSide, partner_id: uuid.UUID) -> uuid.UUID:
        """An empty dossier for a contract made in the system (it has no archive papers)."""
        await self._check_role(partner_id, side)
        dossier = await self.sets.create(
            source_path=f"contract/{uuid.uuid4()}", side=side, file_count=0, partner_id=partner_id
        )
        await self.session.flush()
        return dossier.id

    async def add_file(self, set_id: uuid.UUID, filename: str, data: bytes) -> DocumentFileRead:
        stored = await self.attach_file(set_id, filename, data)
        await self.session.commit()
        return stored

    async def attach_file(self, set_id: uuid.UUID, filename: str, data: bytes) -> DocumentFileRead:
        """Store the bytes and list them in the dossier. Flushes only; the caller commits."""
        if len(data) > self.settings.max_upload_bytes:
            raise AppError(
                "File too large",
                code=ErrorCode.FILE_TOO_LARGE,
                field="file",
                params={"max_bytes": self.settings.max_upload_bytes},
            )
        content_type = _allowed_type(filename)
        dossier = await self._get(set_id)
        if any(link.path == filename for link, _ in await self.set_files.files_of(set_id)):
            raise ConflictError(
                "A file with this name is already in the dossier",
                code=ErrorCode.FILE_NAME_TAKEN,
                field="file",
            )
        file, _ = await self._store(data, content_type)
        await self.set_files.create(set_id=set_id, file_id=file.id, path=filename)
        await self.sets.update(dossier, file_count=dossier.file_count + 1)
        return _file_read(filename, file)

    async def remove_file(self, set_id: uuid.UUID, file_id: uuid.UUID) -> None:
        """Take a file out of the dossier. The stored bytes stay: another dossier may hold them.
        Flushes only; the caller commits."""
        dossier = await self._get(set_id)
        for link, file in await self.set_files.files_of(set_id):
            if file.id == file_id:
                await self.set_files.delete(link)
                await self.sets.update(dossier, file_count=dossier.file_count - 1)
                return
        raise NotFoundError("File not found")

    async def delete_set(self, set_id: uuid.UUID) -> None:
        """Remove an empty contract's dossier. Flushes only; the caller commits."""
        await self.sets.delete(await self._get(set_id))

    async def file_of(self, set_id: uuid.UUID, file_id: uuid.UUID) -> DocumentFileRead:
        """The file if it belongs to the dossier, else not found."""
        for link, file in await self.set_files.files_of(set_id):
            if file.id == file_id:
                return _file_read(link.path, file)
        raise NotFoundError("File not found")

    async def _get(self, set_id: uuid.UUID) -> DocumentSet:
        dossier = await self.sets.get(set_id)
        if dossier is None:
            raise NotFoundError("Document set not found")
        return dossier

    async def get(self, set_id: uuid.UUID) -> DocumentSetDetail:
        dossier = await self._get(set_id)
        partners = await self.partners.summaries([dossier.partner_id] if dossier.partner_id else [])
        return DocumentSetDetail(
            id=dossier.id,
            side=dossier.side,
            partner=partners.get(dossier.partner_id) if dossier.partner_id else None,
            files=[
                _file_read(link.path, file)
                for link, file in await self.set_files.files_of(dossier.id)
            ],
        )

    async def _check_role(self, partner_id: uuid.UUID, side: DocumentSide) -> None:
        partner = await self.partners.get(partner_id)
        holds_side = partner.is_customer if side == DocumentSide.CUSTOMER else partner.is_supplier
        if not holds_side:
            raise ConflictError(
                "Partner does not hold this role",
                code=ErrorCode.PARTNER_ROLE_MISMATCH,
                field="partnerId",
            )

    async def download_url(self, set_id: uuid.UUID, file_id: uuid.UUID) -> DownloadUrl:
        file = await self.file_of(set_id, file_id)
        stored = await self.files.by_sha256(file.sha256)
        if stored is None:
            raise NotFoundError("File not found")
        return DownloadUrl(url=await self.storage.download_url(stored.storage_key, file.path))


# Signed scans and the soft copies the counterparty sends; nothing executable or unreadable.
ALLOWED_TYPES = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def _allowed_type(filename: str) -> str:
    """The content type stored for the file, decided by its extension, not by the browser."""
    suffix = PurePosixPath(filename.lower()).suffix
    if suffix not in ALLOWED_TYPES:
        raise AppError(
            "Only PDF, Word and Excel files can be attached",
            code=ErrorCode.FILE_TYPE_NOT_ALLOWED,
            field="file",
            params={"allowed": ", ".join(ALLOWED_TYPES)},
        )
    return ALLOWED_TYPES[suffix]


def _file_read(path: str, file: DocumentFile) -> DocumentFileRead:
    return DocumentFileRead(
        id=file.id, path=path, size=file.size, content_type=file.content_type, sha256=file.sha256
    )
