# apps/api — FastAPI modular monolith

Python 3.13, managed by **uv** (never pip/poetry). Run everything with `uv run …` from this folder.

## Layout

```
src/app/
  main.py            create_app(): middleware, error handlers, routers, Socket.IO mount, DI
  worker.py          Celery app (task packages listed in autodiscover_tasks)
  core/              cross-cutting infra — no business logic
    config.py        Settings (pydantic-settings, env / .env) + production guards
    database.py      Base, UUIDPrimaryKeyMixin, TimestampMixin, engine/session factories
    ioc.py           Dishka InfrastructureProvider + create_container()
    worker_container.py  container for Celery tasks (no FastAPI, no socket server)
    realtime.py      Socket.IO server (Redis pub/sub), Event base, RealtimePublisher
    exceptions.py    AppError hierarchy (code + optional field), handlers, ERROR_RESPONSES
    security.py      password hashing (argon2), JWT TokenEncoder (access/refresh/one-shot)
    mail.py          EmailSender protocol: console / smtp / outbox implementations
    push.py          PushSender protocol: console / expo / outbox implementations
    storage.py       ObjectStorage: immutable, SHA-256-addressed files on S3/RustFS (ADR 0005)
    rate_limit.py    Redis fixed-window limiter + `rate_limit(scope)` dependency
    request_id.py    RequestIdMiddleware (X-Request-ID, bound to structlog)
    metrics.py       Prometheus counters/histogram + /metrics endpoint
    observability.py optional Sentry init
    openapi.py       operationId = handler name; realtime events added to OpenAPI
    logging.py       structlog
  shared/
    schemas.py       Schema (camelCase base), Page[T], CursorPage[T], ErrorCode, FieldError, ErrorResponse, reject_null
    pagination.py    PageParams (page, pageSize); CursorParams + cursor encode/decode for feeds
    repository.py    BaseRepository[Model] (get/find_one/list/create/update/delete)
    locale.py        Locale, resolve_locale, RequestLocale (Accept-Language dependency)
  modules/
    __init__.py      MODULE_PROVIDERS + MODULE_ROUTERS + REALTIME_EVENTS registry
    <module>/        models · schemas · repository · service · provider · router · tasks · events · templates
                     shipped: auth, users, partners (reference example), documents, contracts, pricing, overview, notifications, health
migrations/          Alembic (async), file names prefixed by date
tests/               pytest against real Postgres + Redis (db `app_test`, redis db 15)
scripts/export_openapi.py   writes ../../packages/api-client/openapi.json
```

## Architecture: DI + repository + service

```
router  ──►  service  ──►  repository  ──►  DB          (inside one module)
               │
               └──►  other module's SERVICE  (never its repository, models or tables)
```

| Layer | May depend on | Must not |
| --- | --- | --- |
| `router.py` | its service, `CurrentUser`, schemas | touch repositories/session, contain logic, raise `HTTPException` |
| `service.py` | its repository, `AsyncSession` (commit), `RealtimePublisher`, **other modules' services** | import or query another module's repository, models or tables |
| `repository.py` | its own model, `BaseRepository` | commit, know about HTTP or other modules |
| `models.py` | `core.database` | ORM `relationship()` across modules (reference by id + FK only) |

`tests/test_architecture.py` fails if a module imports another module's repository. Everything is
wired by Dishka: each module's `provider.py` registers its repository and service; services get
their dependencies through `__init__`.

## Rules

- **Transactions:** repositories `flush()`; services call `await self.session.commit()` after a write. Side effects (Celery `.delay()`, realtime events) go **after** the commit. Read-only methods never commit.
- **Errors:** raise `NotFoundError`, `ConflictError`, `UnauthorizedError`, `ForbiddenError` or an `AppError` subclass. Codes come from the `ErrorCode` enum (`shared/schemas.py`) — add a member for each new case (clients translate by code; typecheck in `packages/i18n` forces the translation). Pass `field="<camelCaseField>"` when the error belongs to one input so forms show it under that field. `message` is an English fallback only; never rely on it for UI.
- **Schemas:** every request/response model inherits `app.shared.schemas.Schema` (camelCase aliases, `from_attributes`). Name them `<Entity>Read/Create/Update/Filter`. Put validation constraints on fields (`Field(min_length=…)`): they become Zod rules in the frontend.
- **Routers:** `APIRouter(prefix=…, tags=[…], route_class=DishkaRoute)`. Inject with `FromDishka[Service]`; auth with `user: CurrentUser`. Always annotate the return type (it becomes the response schema). Path params are camelCase: `Annotated[uuid.UUID, Path(alias="todoId")]` with `"/{todoId}"`.
- **operationId = handler function name**, and the TS SDK is named after it (`list_partners` → `listPartners`, `listPartnersOptions`). Names must be unique across the API (`tests/test_openapi.py` checks this) and should be `verb_noun`.
- **DI:** each module has a `provider.py` (`Provider` with `scope = Scope.REQUEST`, `provide(Class)`); register it in `MODULE_PROVIDERS`. App-wide singletons (engine, Redis, settings, `RealtimePublisher`) live in `core/ioc.py`.
- **Background work:** Celery tasks in `<module>/tasks.py` (`@celery_app.task`), called via `.delay()` after commit. Add the module to `autodiscover_tasks` in `worker.py`. Tasks run eagerly when `ENVIRONMENT=test`. A daily job goes in `beat_schedule` in `worker.py`, run by `pnpm --filter api beat`, with a CLI command in `app/cli.py` to run it by hand.
- **Realtime:** Socket.IO at `/ws/socket.io` on the API origin; clients send `auth: { token }` and join room `user:<id>` (all their devices). Define payloads in `<module>/events.py` (subclass `Event`, set `event_name = "<module>.<what>"`), add them to `REALTIME_EVENTS`, inject `RealtimePublisher` in the service and call `await self.realtime.to_user(user_id, event)` after commit. Run `pnpm codegen` so the frontend gets the typed event.
- **PATCH bodies:** a nullable column is `X | None` (an explicit `null` clears it); a non-nullable one is wrapped with `reject_null("field")` so `{"field": null}` is a 422 instead of a database error. Omitting the field still means "leave it alone".
- **Pagination:** by page number (ADR 0008). The filter subclasses `PageParams` (`page`, `pageSize` ≤ 100); the repository builds the filtered `select` and returns `await self.page(stmt, order_by, params.offset, params.page_size)` → `(rows, total)`, ordering by a total order that ends with a unique column; the service returns `Page[<X>Read](items=…, total=…, page=…, page_size=…)`. Cursor pagination (`CursorParams`, `CursorPage`) is only for unbounded append-only feeds.
- **Auth gates:** `CurrentUser` for anything a signed-in user may do (profile, change password, delete account); `CurrentVerifiedUser` for business endpoints, which answer `403 email_not_verified` while `REQUIRE_EMAIL_VERIFICATION` is on. Unverified users can still log in.
- **Rate limits:** add `Depends(rate_limit("<scope>"))` to credential endpoints (`login`, `register`, `email` scopes exist; add a scope to `Settings.rate_limit_for`). The limiter counts per email (`by_email=True`) or per IP and answers `429 rate_limited` with `Retry-After`.
- **Email:** never send inline. Render a template (`modules/auth/templates.py`), then `send_email.delay(...)` from `modules/users/tasks.py`; the task resolves `EmailSender` from `create_worker_container()`. Local development uses `EMAIL_BACKEND=console` or `smtp` → Mailpit; tests use `outbox`, which collects messages in `OutboxEmailSender.messages`.
- **Push notifications:** other modules call `NotificationService.notify(user_id, copy, data)` after
  their commit, where `copy` is a `PushCopy` (`{locale: PushContent(title, body)}`) built in the
  module's `templates.py`. Delivery is a Celery task that renders each device in the locale it
  registered with (fallback `en`) and deletes tokens Expo reports as dead. Put a deep link in
  `data={"url": "/contracts"}`; the mobile app navigates there on tap. Signing out everywhere forgets
  the user's devices. Backends: `PUSH_BACKEND=console|expo|outbox` (`push_outbox` fixture in tests).
- **Access control** (ADR 0004): check permissions, never roles. Add a `Permission` member in
  `shared/permissions.py`, grant it in the Casbin policy `shared/rbac/policy.csv`, then guard the
  route with `Depends(require_permission(Permission.X))`. Owned data is still filtered by owner in
  the service. Roles (`accountant`, `director`, `admin`) are granted on the Users screen, or with
  `uv run python -m app.cli set-roles <email> <roles…>`.
- **Compatibility** (ADR 0003): change the contract additively. Removing/renaming a field or
  endpoint fails the `api-contract` CI job; follow expand → migrate → `MIN_APP_VERSION` → remove.
  Mobile sends `X-App-Version`; below `MIN_APP_VERSION` every module route answers
  `426 app_update_required`.
- **Configuration** (ADR 0002): add a field to `Settings` without an environment-specific default,
  put the development value in `.env.development` (and `.env.test` if tests need another), and
  inject `Settings` where needed. Never read `os.environ`.
- **Migrations** must be safe on a live table: add columns nullable or with a server default,
  create indexes `CONCURRENTLY` in their own migration, backfill in batches. `pnpm --filter api
  db:lint` (squawk) checks this; `env.py` sets `lock_timeout` so a blocked migration fails fast.
- **Boundaries** are enforced by `lint-imports` (`core`/`shared` never import `modules`) and
  `tests/test_architecture.py`; `deptry` fails on undeclared or unused dependencies.
- **Locale-aware output** (emails, pushes): take `locale: RequestLocale` in the router and pass it
  down; never read headers in services.
- **Observability:** `structlog` only (never `print`), with the request id bound by the middleware. Prometheus counters are labelled by route template. Optional Sentry via `SENTRY_DSN`.

## Adding a module (checklist)

1. `modules/<name>/models.py` — inherit `UUIDPrimaryKeyMixin, TimestampMixin, Base`.
2. `schemas.py`, `repository.py` (subclass `BaseRepository[Model]`, set `model`), `service.py`, `provider.py`, `router.py`.
3. Register provider + router in `modules/__init__.py` (tasks in `worker.py`, events in `REALTIME_EVENTS`).
4. `uv run alembic revision --autogenerate -m "<change>"`, review the file, `uv run alembic upgrade head`.
5. Tests in `tests/test_<name>.py` for the business rules only, using the `client` / `auth_client` / `outbox` / `push_outbox` fixtures (see `docs/testing.md`).
6. From repo root: `pnpm codegen`.

## Commands

```bash
uv sync                                  # install
uv add <pkg> / uv add --dev <pkg>        # dependencies (updates uv.lock; commit it)
uv run fastapi dev src/app/main.py       # http://localhost:8000/docs
uv run celery -A app.worker worker -l info
uv run alembic upgrade head | uv run alembic check
uv run ruff check --fix . && uv run ruff format .
uv run mypy src                          # strict
uv run lint-imports && uv run deptry src # layer contracts, declared dependencies
uv run pytest                            # needs `pnpm infra:up` (real Postgres + Redis)
uv run pytest tests/test_partners.py -q  # one file while iterating
```

Done = `pnpm --filter api lint`, `mypy src`, `alembic check`, `pytest` (and `db:lint` for a new migration) all pass, and `pnpm codegen` was run if any schema/route changed.
