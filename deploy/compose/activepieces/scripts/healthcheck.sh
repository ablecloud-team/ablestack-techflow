#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
deploy_dir=$(cd -- "${script_dir}/.." && pwd)
wait_seconds=0

if [[ ${1:-} == "--wait" ]]; then
  wait_seconds=${2:-300}
fi

cd "${deploy_dir}"
set -a
source .env
set +a

deadline=$((SECONDS + wait_seconds))
services=(postgres redis app worker event-gateway ingress)

while true; do
  healthy=true
  for service in "${services[@]}"; do
    container_id=$(docker compose --env-file .env ps -q "${service}")
    if [[ -z ${container_id} ]]; then
      healthy=false
      continue
    fi
    state=$(docker inspect --format '{{.State.Status}}' "${container_id}")
    health=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "${container_id}")
    if [[ ${state} != "running" || ${health} != "healthy" ]]; then
      healthy=false
    fi
  done
  worker_id=$(docker compose --env-file .env ps -q worker)
  worker_logs=$(docker logs "${worker_id}" 2>&1 || true)
  if [[ -z ${worker_id} || ${worker_logs} != *"Polling worker started"* ]]; then
    healthy=false
  fi

  if ${healthy}; then
    break
  fi
  if (( SECONDS >= deadline )); then
    docker compose --env-file .env ps
    echo "Services did not become healthy within ${wait_seconds} seconds." >&2
    exit 1
  fi
  sleep 5
done

private_url="http://${AP_BIND_ADDRESS}:${AP_HTTP_PORT}"
curl -fsS "${private_url}/api/v1/health" >/dev/null
curl -fsS "${private_url}/techflow/hooks/healthz" >/dev/null
if [[ -n ${TECHFLOW_PUBLIC_URL:-} ]]; then
  curl -fsS "${TECHFLOW_PUBLIC_URL}/api/v1/health" >/dev/null
fi
docker compose --env-file .env exec -T postgres \
  pg_isready -U "${AP_POSTGRES_USERNAME}" -d "${AP_POSTGRES_DATABASE}" >/dev/null
docker compose --env-file .env exec -T redis sh -c \
  'REDISCLI_AUTH="$AP_REDIS_PASSWORD" redis-cli ping' | grep -q PONG

echo "ingress=healthy event_gateway=healthy app=healthy worker=healthy worker_polling=ready postgres=healthy redis=healthy"
