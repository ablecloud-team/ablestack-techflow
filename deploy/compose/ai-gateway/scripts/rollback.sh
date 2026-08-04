#!/usr/bin/env bash
set -euo pipefail

compose_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$compose_dir"

: "${TECHFLOW_RAG_PREVIOUS_RELEASE:?set the previously verified immutable release tag}"
export TECHFLOW_RAG_RELEASE="$TECHFLOW_RAG_PREVIOUS_RELEASE"
docker compose --env-file .env up -d --no-deps gateway
docker compose --env-file .env ps gateway
