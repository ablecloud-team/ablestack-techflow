#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
deploy_dir=$(cd -- "${script_dir}/.." && pwd)

cd "${deploy_dir}"
set -a
source .env
set +a

docker compose --env-file .env ps
curl -fsS "${AP_FRONTEND_URL}/api/v1/health"
printf '\n'
worker_id=$(docker compose --env-file .env ps -q worker)
worker_logs=$(docker logs "${worker_id}" 2>&1 || true)
if [[ ${worker_logs} == *"Polling worker started"* ]]; then
  echo "worker_polling=ready"
else
  echo "worker_polling=not_ready"
fi
docker stats --no-stream \
  --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}' \
  $(docker compose --env-file .env ps -q)
