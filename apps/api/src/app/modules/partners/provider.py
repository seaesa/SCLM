from dishka import Provider, Scope, provide

from app.modules.partners.repository import (
    ConflictRepository,
    ExternalRefRepository,
    PartnerRepository,
)
from app.modules.partners.service import PartnerService


class PartnersProvider(Provider):
    scope = Scope.REQUEST

    partners = provide(PartnerRepository)
    refs = provide(ExternalRefRepository)
    conflicts = provide(ConflictRepository)
    service = provide(PartnerService)
