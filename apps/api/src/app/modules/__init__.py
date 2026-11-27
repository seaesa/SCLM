"""Module registry.

Adding a module = create `app/modules/<name>/` (models, schemas, repository,
service, provider, router, tasks, events) and register it below. Celery tasks are
also listed in `app/worker.py`.
"""

from fastapi import APIRouter

from app.core.realtime import Event
from app.modules.archive.provider import ArchiveProvider
from app.modules.auth.provider import AuthProvider
from app.modules.auth.router import router as auth_router
from app.modules.contracts.provider import ContractsProvider
from app.modules.contracts.router import router as contracts_router
from app.modules.documents.provider import DocumentsProvider
from app.modules.documents.router import router as documents_router
from app.modules.health.router import router as health_router
from app.modules.notifications.provider import NotificationsProvider
from app.modules.notifications.router import router as notifications_router
from app.modules.overview.provider import OverviewProvider
from app.modules.overview.router import router as overview_router
from app.modules.partners.provider import PartnersProvider
from app.modules.partners.router import router as partners_router
from app.modules.pricing.provider import PricingProvider
from app.modules.pricing.router import router as pricing_router
from app.modules.seed.provider import SeedProvider
from app.modules.users.provider import UsersProvider
from app.modules.users.router import router as users_router

MODULE_PROVIDERS = [
    UsersProvider,
    AuthProvider,
    NotificationsProvider,
    PartnersProvider,
    DocumentsProvider,
    ContractsProvider,
    PricingProvider,
    OverviewProvider,
    ArchiveProvider,
    SeedProvider,
]

MODULE_ROUTERS: list[APIRouter] = [
    health_router,
    auth_router,
    users_router,
    notifications_router,
    partners_router,
    documents_router,
    contracts_router,
    pricing_router,
    overview_router,
]

# Socket.IO payloads, exported to OpenAPI so the frontend gets typed events.
REALTIME_EVENTS: list[type[Event]] = []
