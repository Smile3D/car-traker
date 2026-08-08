#!/usr/bin/env bash
# Run on the VM to pull and recreate one or all app services.
# Usage: ./scripts/deploy-on-vm.sh [backend|frontend|all]
set -euo pipefail

SERVICE="${1:-all}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
REGISTRY_HOST="${REGISTRY_HOST:-europe-central2-docker.pkg.dev}"

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "Missing $COMPOSE_FILE in $(pwd)" >&2
  exit 1
fi

if command -v gcloud >/dev/null 2>&1; then
  gcloud auth configure-docker "$REGISTRY_HOST" --quiet
fi

if [[ "$SERVICE" == "all" ]]; then
  docker compose -f "$COMPOSE_FILE" pull
  docker compose -f "$COMPOSE_FILE" up -d --force-recreate
else
  docker compose -f "$COMPOSE_FILE" pull "$SERVICE"
  docker compose -f "$COMPOSE_FILE" up -d --no-deps --force-recreate "$SERVICE"
fi

docker compose -f "$COMPOSE_FILE" ps
