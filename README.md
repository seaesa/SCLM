# SPIDER — Contract Lifecycle Management

Contracts and addenda of Spider (customers, contractors, warehouse leases): the scanned archive,
renewal chains, approval and signing of new documents, due dates and notice deadlines.

| Path                  | Stack                                                                              |
| --------------------- | ---------------------------------------------------------------------------------- |
| `apps/api`            | FastAPI · SQLAlchemy 2 async + Alembic · PostgreSQL · Redis · Celery · Casbin · uv |
| `apps/web`            | Next.js 16 · shadcn/ui (base-maia) · Tailwind v4 · react-pdf                       |
| `apps/mobile`         | Expo SDK 58 (sign-in and profile only; contract work is web-only)                  |
| `packages/api-client` | Generated from OpenAPI: types, Zod, SDK, React Query options                       |
| `packages/core`       | Shared hooks, stores and form logic                                                |
| `packages/i18n`       | User-facing text (Vietnamese)                                                      |
| `packages/theme`      | Design tokens                                                                      |

Contract files live in S3-compatible storage (RustFS), stored once under their content hash
(`sha256/<hash>`); the original names and folders are kept in the database. Roles: `admin`,
`accountant`, `director` (`apps/api/src/app/shared/rbac/policy.csv`).

## Run locally

Requirements: Docker and [mise](https://mise.jdx.dev). `mise install` provides Node, pnpm,
Python and uv at the versions in `mise.toml`. Development settings are committed in
`apps/*/.env.development`; personal overrides go in an ignored `.env`.

### 1. Install and start the services

```bash
mise install
pnpm install
(cd apps/api && uv sync)
pnpm infra:up      # Postgres :5432 · Redis :6379 · Mailpit :8025 · RustFS :9000 (console :9001)
```

### 2. Create and migrate the database

```bash
docker compose exec postgres createdb -U postgres sclm   # once; "already exists" is fine
pnpm --filter api db:migrate
```

### 3. Load the data (seed bundle)

The seed bundle is `docs/business/data` (git-ignored: it holds business data). Its manifest
`seed.json` lists the users, partner exports, scan folders and the extracted archive. Get the
folder from the team, then:

```bash
cd apps/api
uv run python -m app.cli seed ../../docs/business/data   # ~1–2 min the first time
uv run python -m app.cli set-password admin@example.com   # dev: set a password without email
```

Steps whose input has not changed are skipped, so the command is safe to rerun
(`--only users partners files archive fuel-prices`, `--force` to redo).

### 4. Run

```bash
pnpm dev:web                   # API http://localhost:8000/docs · web http://localhost:3000
pnpm --filter api worker       # Celery: emails (set-password links)
pnpm --filter api beat         # nightly status refresh, hourly Petrolimex prices (optional in dev)
```

Emails are only logged in development (`EMAIL_BACKEND=console`); set `EMAIL_BACKEND=smtp`,
`SMTP_HOST=localhost` and `SMTP_PORT=1025` in `apps/api/.env` to see them in Mailpit at
http://localhost:8025.

### Reset the database

```bash
docker compose exec postgres psql -U postgres -c "DROP DATABASE sclm WITH (FORCE)" -c "CREATE DATABASE sclm"
pnpm --filter api db:migrate
(cd apps/api && uv run python -m app.cli seed ../../docs/business/data --force)
```

Stored files stay in RustFS (same hash, same object), so a reseed does not upload them again.

### Useful commands (`apps/api`, `uv run python -m app.cli …`)

| Command                                 | Does                                                       |
| --------------------------------------- | ---------------------------------------------------------- |
| `create-user <email> "<name>" --role X` | Create an account (prompts for the password)               |
| `set-roles <email> <roles…>`            | Change roles                                               |
| `set-password <email>`                  | Set a password without the email link                      |
| `find-file <name or hash>`              | Where a scan is stored (object key, dossier)               |
| `refresh-contracts`                     | Recompute statuses, codes and due dates (after an upgrade) |
| `sync-fuel-prices`                      | Fetch today's Petrolimex prices                            |

## Deploy

One machine runs the whole stack with `docker-compose.full.yml` (Postgres, Redis, RustFS, API,
worker, beat, web), driven by `scripts/live.sh`:

```bash
scripts/live.sh init          # writes .env.live with generated secrets (never overwritten)
# edit .env.live: WEB_ORIGIN, API_ORIGIN, STORAGE_PUBLIC_URL = the public addresses
scripts/live.sh up            # build and start; the API migrates the database first
scripts/live.sh seed          # load the seed bundle from docs/business/data (idempotent)
scripts/live.sh backup [dir]  # database dump + stored files + .env.live
scripts/live.sh restore <dir> # move to another machine: restore there, then adjust the origins
```

After an upgrade that changes how contracts are derived, run
`docker compose -p sclm-live --env-file .env.live -f docker-compose.full.yml run --rm api python -m app.cli refresh-contracts`.

Ports are bound to `127.0.0.1`: put a reverse proxy with HTTPS in front of web (`:3100`),
API (`:8100`) and file downloads (`:9100`). Keep `.env.live` with every backup, and keep backups
off the machine: without it the data cannot be read. Environment variables, scaling and the
security checklist: [docs/deployment.md](docs/deployment.md).

## Development

```bash
pnpm codegen   # after any API schema/route change: regenerates packages/api-client
pnpm check     # every gate CI runs (format, lint, dependency rules, spelling, types, tests)
```

Rules and where code goes: [AGENTS.md](./AGENTS.md) · [architecture](docs/architecture.md) ·
[adding a feature](docs/adding-a-feature.md) · [testing](docs/testing.md) ·
[conventions](docs/conventions.md) · decisions in [docs/adr](docs/adr).
Business analysis and the archive digitization report are in `docs/business/`.
