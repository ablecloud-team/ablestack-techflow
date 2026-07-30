#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
deploy_dir=$(cd -- "${script_dir}/.." && pwd)

cd "${deploy_dir}"
set -a
source .env
set +a

table_count_before=$(docker compose --env-file .env exec -T postgres \
  psql -U "${AP_POSTGRES_USERNAME}" -d "${AP_POSTGRES_DATABASE}" -Atc \
  "select count(*) from information_schema.tables where table_schema='public';")

probe_value=$(date -u +%Y%m%dT%H%M%SZ)
docker compose --env-file .env exec -T redis sh -c \
  'REDISCLI_AUTH="$AP_REDIS_PASSWORD" redis-cli SET techflow:deployment:probe "$1" >/dev/null' \
  sh "${probe_value}"

docker compose --env-file .env restart postgres redis
"${script_dir}/healthcheck.sh" --wait 180

table_count_after=$(docker compose --env-file .env exec -T postgres \
  psql -U "${AP_POSTGRES_USERNAME}" -d "${AP_POSTGRES_DATABASE}" -Atc \
  "select count(*) from information_schema.tables where table_schema='public';")
redis_value=$(docker compose --env-file .env exec -T redis sh -c \
  'REDISCLI_AUTH="$AP_REDIS_PASSWORD" redis-cli GET techflow:deployment:probe')

if [[ ${table_count_before} != "${table_count_after}" ]]; then
  echo "PostgreSQL table count changed across restart." >&2
  exit 1
fi
if [[ ${redis_value} != "${probe_value}" ]]; then
  echo "Redis persistence probe was not recovered." >&2
  exit 1
fi

docker compose --env-file .env exec -T redis sh -c \
  'REDISCLI_AUTH="$AP_REDIS_PASSWORD" redis-cli DEL techflow:deployment:probe >/dev/null'

echo "postgres=persistent redis=persistent"
