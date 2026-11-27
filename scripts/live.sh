#!/usr/bin/env bash
# The live environment: real contract data in docker-compose.full.yml, secrets in .env.live.
# Moving to a server later is `backup` here and `restore` there; nothing is re-entered.
set -euo pipefail
cd "$(dirname "$0")/.."

ENV_FILE=.env.live
DATA=docs/business/data
compose() { docker compose --env-file "$ENV_FILE" -f docker-compose.full.yml "$@"; }
cli() { compose run --rm -T "$@"; }

case "${1:-help}" in
  init) # Generate secrets once; never overwrite them (they unlock the data).
    [[ -e $ENV_FILE ]] && { echo "$ENV_FILE exists, keeping it"; exit 0; }
    umask 077
    cat > "$ENV_FILE" <<CONF
POSTGRES_PASSWORD=$(openssl rand -hex 24)
JWT_SECRET=$(openssl rand -hex 32)
STORAGE_ACCESS_KEY=sclm-$(openssl rand -hex 6)
STORAGE_SECRET_KEY=$(openssl rand -hex 24)
WEB_ORIGIN=http://localhost:3100
API_ORIGIN=http://localhost:8100
STORAGE_PUBLIC_URL=http://localhost:9100
CONF
    echo "Wrote $ENV_FILE. Keep a copy with the backups: without it the data cannot be read." ;;
  up) compose up -d --build ;;
  down) compose down ;;
  logs) shift; compose logs -f "$@" ;;
  seed) # live.sh seed [--only step...] [--force]: loads the seed bundle (docs/business/data,
    # manifest seed.json). Steps whose input is unchanged are skipped, so it is safe to rerun.
    shift
    cli -v "$PWD/$DATA:/seed:ro" api python -m app.cli seed /seed "$@" ;;
  user) # live.sh user <email> "<full name>" <role> [role...]: asks for the password.
    shift; email=$1 name=$2; shift 2; role=$1; shift
    compose run --rm api python -m app.cli create-user "$email" "$name" --role "$role"
    [[ $# -gt 0 ]] && cli api python -m app.cli set-roles "$email" "$role" "$@" || true ;;
  backup) # live.sh backup [dir]: database dump + every stored file + the secrets.
    dir=${2:-$HOME/SCLM-backups}/$(date +%Y%m%d-%H%M%S); mkdir -p "$dir"
    compose exec -T postgres pg_dump -U postgres -Fc sclm > "$dir/db.dump"
    docker run --rm -v sclm-live_rustfs-data:/data:ro -v "$dir:/out" alpine \
      tar czf /out/files.tgz -C /data .
    cp "$ENV_FILE" "$dir/env.live"
    echo "Backup in $dir" ;;
  restore) # live.sh restore <backup dir>: into an empty live environment.
    dir=$2; cp -n "$dir/env.live" "$ENV_FILE" || true
    compose up -d postgres rustfs && compose stop rustfs
    docker run --rm -v sclm-live_rustfs-data:/data -v "$dir:/in:ro" alpine \
      tar xzf /in/files.tgz -C /data
    until compose exec -T postgres pg_isready -U postgres >/dev/null; do sleep 1; done
    compose exec -T postgres pg_restore -U postgres -d sclm --clean --if-exists < "$dir/db.dump"
    compose up -d --build ;;
  *) echo "usage: scripts/live.sh init|up|down|logs|seed|user|backup|restore" ;;
esac
