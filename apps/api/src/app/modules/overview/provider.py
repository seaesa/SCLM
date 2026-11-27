from dishka import Provider, Scope, provide

from app.modules.overview.service import OverviewService


class OverviewProvider(Provider):
    scope = Scope.REQUEST

    service = provide(OverviewService)
