#!/usr/bin/env bash
# Pull and recreate services without `docker compose down` (DB stays up).
# Usage: IMAGE_TAG=<sha|latest> ./scripts/deploy-on-vm.sh [backend|frontend|all]
set -euo pipefail

SERVICE="${1:-all}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
REGISTRY_HOST="${REGISTRY_HOST:-europe-central2-docker.pkg.dev}"
export IMAGE_TAG="${IMAGE_TAG:-latest}"

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "Missing $COMPOSE_FILE in $(pwd)" >&2
  exit 1
fi

if command -v gcloud >/dev/null 2>&1; then
  gcloud auth configure-docker "$REGISTRY_HOST" --quiet
fi

# pull + up -d: recreate only containers whose image changed.
# Never `compose down` — that stops db and causes full downtime.
if [[ "$SERVICE" == "all" ]]; then
  docker compose -f "$COMPOSE_FILE" pull
  docker compose -f "$COMPOSE_FILE" up -d --remove-orphans
else
  docker compose -f "$COMPOSE_FILE" pull "$SERVICE"
  docker compose -f "$COMPOSE_FILE" up -d --no-deps --remove-orphans "$SERVICE"
fi

docker compose -f "$COMPOSE_FILE" ps
docker image prune -f >/dev/null 2>&1 || true
