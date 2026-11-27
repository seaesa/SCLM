import uuid
from collections.abc import Sequence

from sqlalchemy import or_, select

from app.modules.documents.models import DocumentFile, DocumentSet, DocumentSetFile
from app.shared.repository import BaseRepository


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class DocumentFileRepository(BaseRepository[DocumentFile]):
    model = DocumentFile

    async def by_sha256(self, sha256: str) -> DocumentFile | None:
        return await self.find_one(DocumentFile.sha256 == sha256)


class DocumentSetRepository(BaseRepository[DocumentSet]):
    model = DocumentSet

    async def by_source_path(self, source_path: str) -> DocumentSet | None:
        return await self.find_one(DocumentSet.source_path == source_path)


class DocumentSetFileRepository(BaseRepository[DocumentSetFile]):
    model = DocumentSetFile

    async def files_of(self, set_id: uuid.UUID) -> Sequence[tuple[DocumentSetFile, DocumentFile]]:
        query = (
            select(DocumentSetFile, DocumentFile)
            .join(DocumentFile, DocumentFile.id == DocumentSetFile.file_id)
            .where(DocumentSetFile.set_id == set_id)
            .order_by(DocumentSetFile.path)
        )
        return [(link, file) for link, file in await self.session.execute(query)]

    async def matching(
        self, term: str, limit: int
    ) -> Sequence[tuple[DocumentSetFile, DocumentFile, DocumentSet]]:
        """Filed copies whose path contains `term`, or whose hash starts with it."""
        query = (
            select(DocumentSetFile, DocumentFile, DocumentSet)
            .join(DocumentFile, DocumentFile.id == DocumentSetFile.file_id)
            .join(DocumentSet, DocumentSet.id == DocumentSetFile.set_id)
            .where(
                or_(
                    DocumentSetFile.path.ilike(f"%{_escape_like(term)}%", escape="\\"),
                    DocumentFile.sha256.startswith(term.lower()),
                )
            )
            .order_by(DocumentSetFile.path)
            .limit(limit)
        )
        return [(link, file, dossier) for link, file, dossier in await self.session.execute(query)]
