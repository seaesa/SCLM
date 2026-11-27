from dishka import Provider, Scope, provide

from app.modules.pricing.petrolimex import FuelPriceSource, PetrolimexPrices
from app.modules.pricing.repository import (
    FuelClauseRepository,
    FuelPriceRepository,
    PriceLineRepository,
    PriceTableRepository,
)
from app.modules.pricing.service import PricingService


class PricingProvider(Provider):
    scope = Scope.REQUEST

    tables = provide(PriceTableRepository)
    lines = provide(PriceLineRepository)
    clauses = provide(FuelClauseRepository)
    fuel_prices = provide(FuelPriceRepository)
    service = provide(PricingService)
    fuel_price_source = provide(PetrolimexPrices, provides=FuelPriceSource, scope=Scope.APP)
