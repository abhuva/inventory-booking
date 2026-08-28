#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/docker/inventory}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
BRANCH="${BRANCH:-main}"

cd "$APP_DIR"

echo "Deploying inventory booking from origin/${BRANCH}"

git fetch origin "$BRANCH"
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

if [[ ! -f .env ]]; then
  echo "Missing production .env in $APP_DIR" >&2
  exit 1
fi

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "Missing Compose file: $APP_DIR/$COMPOSE_FILE" >&2
  exit 1
fi

docker compose -f "$COMPOSE_FILE" config >/tmp/inventory-compose-config.out
docker compose -f "$COMPOSE_FILE" up -d --build
docker compose -f "$COMPOSE_FILE" exec -T backend uv run alembic upgrade head

docker compose -f "$COMPOSE_FILE" ps

docker compose -f "$COMPOSE_FILE" exec -T backend python - <<'PY'
from urllib.request import urlopen

for url in (
    "http://127.0.0.1:8000/health",
    "http://127.0.0.1:8000/health/database",
):
    with urlopen(url, timeout=10) as response:
        print(url, response.status, response.read().decode())
PY

echo "Deploy complete."
