#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
deploy_dir=$(cd -- "${script_dir}/.." && pwd)
backup_dir=${TECHFLOW_BACKUP_DIR:-/var/backups/ablestack-techflow/state}
retention_days=7
label=manual
probe_id=

usage() {
  echo "Usage: $0 [--label NAME] [--retention-days DAYS] [--probe-id ID] [--output-dir PATH]"
}

while (($#)); do
  case "$1" in
    --label)
      label=${2:?missing label}
      shift 2
      ;;
    --retention-days)
      retention_days=${2:?missing retention days}
      shift 2
      ;;
    --probe-id)
      probe_id=${2:?missing probe ID}
      shift 2
      ;;
    --output-dir)
      backup_dir=${2:?missing output directory}
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
done

[[ ${label} =~ ^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$ ]] || {
  echo "Invalid backup label." >&2
  exit 2
}
[[ ${retention_days} =~ ^[1-9][0-9]{0,3}$ ]] || {
  echo "Retention days must be between 1 and 9999." >&2
  exit 2
}
if [[ -n ${probe_id} && ! ${probe_id} =~ ^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}$ ]]; then
  echo "Invalid probe ID." >&2
  exit 2
fi

cd "${deploy_dir}"
set -a
source .env
set +a

umask 027
install -d -m 0750 -o root -g ablecloud "${backup_dir}"
lock_file="${backup_dir}/.backup.lock"
exec 9>"${lock_file}"
flock -n 9 || {
  echo "Another TechFlow backup is already running." >&2
  exit 1
}

started_epoch=$(date +%s)
created_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
stamp=$(date -u +%Y%m%dT%H%M%SZ)
staging=$(mktemp -d "${backup_dir}/.${stamp}.XXXXXX")
archive="${backup_dir}/techflow-state-${stamp}-${label}.tar.gz"

cleanup() {
  rm -rf -- "${staging}"
}
trap cleanup EXIT

postgres_image=$(docker compose --env-file .env config --images | grep -F 'pgvector/pgvector:' | head -n 1)
redis_image=$(docker compose --env-file .env config --images | grep -E '^redis:' | head -n 1)

docker compose --env-file .env exec -T postgres \
  pg_dump -U "${AP_POSTGRES_USERNAME}" -d "${AP_POSTGRES_DATABASE}" \
  --format=custom --no-owner --no-privileges >"${staging}/postgres.dump"

docker compose --env-file .env exec -T redis sh -c '
  set -eu
  output=/tmp/techflow-backup.rdb
  rm -f "$output"
  REDISCLI_AUTH="$AP_REDIS_PASSWORD" redis-cli --rdb "$output" >/dev/null
  cat "$output"
  rm -f "$output"
' >"${staging}/redis.rdb"

database_bytes=$(docker compose --env-file .env exec -T postgres \
  psql -U "${AP_POSTGRES_USERNAME}" -d "${AP_POSTGRES_DATABASE}" -Atc \
  "select pg_database_size(current_database());")
table_count=$(docker compose --env-file .env exec -T postgres \
  psql -U "${AP_POSTGRES_USERNAME}" -d "${AP_POSTGRES_DATABASE}" -Atc \
  "select count(*) from information_schema.tables where table_schema='public';")
redis_key_count=$(docker compose --env-file .env exec -T redis sh -c \
  'REDISCLI_AUTH="$AP_REDIS_PASSWORD" redis-cli --raw DBSIZE')

python3 "${script_dir}/backup_manifest.py" create \
  --directory "${staging}" \
  --created-at "${created_at}" \
  --label "${label}" \
  --postgres-image "${postgres_image}" \
  --redis-image "${redis_image}" \
  --database "${AP_POSTGRES_DATABASE}" \
  --database-bytes "${database_bytes}" \
  --table-count "${table_count}" \
  --redis-key-count "${redis_key_count}" \
  --probe-id "${probe_id}"

(
  cd "${staging}"
  sha256sum manifest.json postgres.dump redis.rdb >checksums.sha256
)
tar -C "${staging}" -czf "${archive}" \
  manifest.json checksums.sha256 postgres.dump redis.rdb
chown root:ablecloud "${archive}"
chmod 0640 "${archive}"

if tar -tzf "${archive}" | grep -Eq '(^|/)(\.env|activepieces\.env|secret-audit\.jsonl)$'; then
  echo "Backup archive contains a forbidden secret-bearing file." >&2
  rm -f -- "${archive}"
  exit 1
fi

find "${backup_dir}" -maxdepth 1 -type f \
  -name 'techflow-state-*.tar.gz' -mtime "+${retention_days}" -delete

duration=$(( $(date +%s) - started_epoch ))
size=$(stat -c %s "${archive}")
echo "backup=created archive=${archive} bytes=${size} duration_seconds=${duration} retention_days=${retention_days} secrets=excluded"
echo "${archive}"
