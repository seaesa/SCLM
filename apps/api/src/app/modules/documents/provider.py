from dishka import Provider, Scope, provide

from app.modules.documents.repository import (
    DocumentFileRepository,
    DocumentSetFileRepository,
    DocumentSetRepository,
)
from app.modules.documents.service import DocumentService


class DocumentsProvider(Provider):
    scope = Scope.REQUEST

    files = provide(DocumentFileRepository)
    sets = provide(DocumentSetRepository)
    set_files = provide(DocumentSetFileRepository)
    service = provide(DocumentService)
