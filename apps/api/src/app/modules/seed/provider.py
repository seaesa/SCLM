from dishka import Provider, Scope, provide

from app.modules.seed.repository import SeedRunRepository
from app.modules.seed.service import SeedService


class SeedProvider(Provider):
    scope = Scope.REQUEST

    runs = provide(SeedRunRepository)
    service = provide(SeedService)
