from dishka import Provider, Scope, provide

from app.modules.archive.service import ArchiveService


class ArchiveProvider(Provider):
    scope = Scope.REQUEST

    service = provide(ArchiveService)
