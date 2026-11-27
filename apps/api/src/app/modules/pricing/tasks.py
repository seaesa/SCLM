"""Celery tasks. Tasks stay thin: they run container work through `run_async`."""

from dishka import AsyncContainer

from app.core.worker_container import run_async
from app.modules.pricing.petrolimex import FuelPriceSource
from app.modules.pricing.service import PricingService
from app.worker import celery_app


async def _sync(container: AsyncContainer) -> None:
    async with container() as request:
        service = await request.get(PricingService)
        await service.sync_fuel_prices(await request.get(FuelPriceSource))


@celery_app.task
def sync_fuel_prices() -> None:
    """Hourly: record the retail fuel prices Petrolimex publishes."""
    run_async(_sync)
