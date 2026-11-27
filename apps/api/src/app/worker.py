import os
import sys

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

# On platforms where billiard starts pool processes with `spawn` (macOS on Python 3.12+,
# Windows) the child never inherits the parent's tracer registry, so every task dies with
# `ValueError: not enough values to unpack (expected 3, got 0)` in `fast_trace_task`.
# This flag makes the child rebuild its own optimizations instead of relying on fork.
if sys.platform == "darwin" or os.name == "nt":
    os.environ.setdefault("FORKED_BY_MULTIPROCESSING", "1")

settings = get_settings()

celery_app = Celery(
    "app",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_always_eager=settings.environment == "test",
)
celery_app.conf.beat_schedule = {
    # 17:05 UTC is 00:05 in Vietnam: statuses follow the new day before anyone looks.
    "refresh-contract-statuses": {
        "task": "app.modules.contracts.tasks.refresh_contract_statuses",
        "schedule": crontab(hour=17, minute=5),
    },
    # Petrolimex changes prices at 15:00 Vietnam time; an hourly sync records them the same day.
    "sync-fuel-prices": {
        "task": "app.modules.pricing.tasks.sync_fuel_prices",
        "schedule": crontab(minute=10),
    },
}
celery_app.autodiscover_tasks(
    [
        "app.modules.users",
        "app.modules.notifications",
        "app.modules.contracts",
        "app.modules.pricing",
    ]
)
