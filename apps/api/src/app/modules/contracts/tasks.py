"""Celery tasks. Tasks stay thin: they run container work through `run_async`."""

from dishka import AsyncContainer

from app.core.worker_container import run_async
from app.modules.contracts.service import ContractService
from app.shared.clock import business_today
from app.worker import celery_app


async def _refresh(container: AsyncContainer) -> None:
    async with container() as request:
        service = await request.get(ContractService)
        await service.refresh_all(business_today())


@celery_app.task
def refresh_contract_statuses() -> None:
    """Daily, just after midnight in Vietnam: statuses that changed because the date moved."""
    run_async(_refresh)
