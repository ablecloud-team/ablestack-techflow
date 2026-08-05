#!/usr/bin/env bash
set -euo pipefail

compose_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$compose_dir"

test -f .env || { echo ".env is required; copy .env.example and use protected secret-file paths" >&2; exit 1; }
docker compose --env-file .env config --quiet
docker compose --env-file .env build --pull gateway migrate source-mirror-init source-reconciler
docker compose --env-file .env up -d database
docker compose --env-file .env run --rm migrate
docker compose --env-file .env up -d gateway source-reconciler
docker compose --env-file .env ps
