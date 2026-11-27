import uuid

from app.modules.documents.models import DocumentSide
from app.modules.partners.schemas import PartnerSummary
from app.shared.schemas import Schema


class DocumentFileRead(Schema):
    id: uuid.UUID
    path: str
    size: int
    content_type: str
    sha256: str


class DocumentSetDetail(Schema):
    id: uuid.UUID
    side: DocumentSide
    partner: PartnerSummary | None
    files: list[DocumentFileRead]


class DownloadUrl(Schema):
    url: str


class StoreReport(Schema):
    files_stored: int = 0
    files_already_stored: int = 0


class LocatedFile(Schema):
    """Where a stored file was filed and the object that holds its bytes."""

    path: str
    sha256: str
    storage_key: str
    size: int
    dossier: str
