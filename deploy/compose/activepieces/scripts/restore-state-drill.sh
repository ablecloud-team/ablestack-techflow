#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
deploy_dir=$(cd -- "${script_dir}/.." && pwd)
backup_dir=${TECHFLOW_BACKUP_DIR:-/var/backups/ablestack-techflow/state}
archive=
evidence_output=
keep_failed=false

usage() {
  echo "Usage: $0 [--archive FILE] [--evidence-output FILE] [--keep-failed]"
}

while (($#)); do
  case "$1" in
    --archive)
      archive=${2:?missing archive}
      shift 2
      ;;
    --evidence-output)
      evidence_output=${2:?missing evidence output}
      shift 2
      ;;
    --keep-failed)
      keep_failed=true
      shift
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

if [[ -z ${archive} ]]; then
  archive=$(find "${backup_dir}" -maxdepth 1 -type f \
    -name 'techflow-state-*.tar.gz' -printf '%T@ %p\n' |
    sort -nr | head -n 1 | cut -d' ' -f2-)
fi
[[ -f ${archive} ]] || {
  echo "Backup archive not found: ${archive}" >&2
  exit 1
}

cd "${deploy_dir}"
set -a
source .env
set +a

started_epoch=$(date +%s)
run_id="issue16-$(date -u +%Y%m%dT%H%M%SZ)-$$"
workdir=$(mktemp -d "/var/tmp/techflow-recovery.${run_id}.XXXXXX")
network="techflow-recovery-${run_id}"
pg_container="techflow-recovery-pg-${run_id}"
redis_container="techflow-recovery-redis-${run_id}"
pg_volume="techflow-recovery-pg-${run_id}"
redis_volume="techflow-recovery-redis-${run_id}"
drill_password=$(openssl rand -hex 24)
succeeded=false

cleanup() {
  if ${succeeded} || ! ${keep_failed}; then
    docker rm -f "${pg_container}" "${redis_container}" >/dev/null 2>&1 || true
    docker network rm "${network}" >/dev/null 2>&1 || true
    docker volume rm "${pg_volume}" "${redis_volume}" >/dev/null 2>&1 || true
    rm -rf -- "${workdir}"
  else
    echo "Failed drill resources retained: ${run_id}" >&2
  fi
}
trap cleanup EXIT

if tar -tzf "${archive}" | grep -Eq '(^/|(^|/)\.\.(/|$))'; then
  echo "Unsafe archive path detected." >&2
  exit 1
fi
tar -C "${workdir}" -xzf "${archive}"
(
  cd "${workdir}"
  sha256sum -c checksums.sha256
)
python3 "${script_dir}/backup_manifest.py" verify --directory "${workdir}"

manifest="${workdir}/manifest.json"
postgres_image=$(python3 "${script_dir}/backup_manifest.py" read --manifest "${manifest}" --field source.postgresImage)
redis_image=$(python3 "${script_dir}/backup_manifest.py" read --manifest "${manifest}" --field source.redisImage)
database=$(python3 "${script_dir}/backup_manifest.py" read --manifest "${manifest}" --field postgres.database)
expected_tables=$(python3 "${script_dir}/backup_manifest.py" read --manifest "${manifest}" --field postgres.publicTableCount)
source_observed_redis_keys=$(
  python3 "${script_dir}/backup_manifest.py" read \
    --manifest "${manifest}" --field redis.sourceObservedKeyCount 2>/dev/null ||
  python3 "${script_dir}/backup_manifest.py" read \
    --manifest "${manifest}" --field redis.keyCount
)
probe_id=$(python3 "${script_dir}/backup_manifest.py" read --manifest "${manifest}" --field postgres.probeId)

docker network create --internal "${network}" >/dev/null
docker volume create "${pg_volume}" >/dev/null
docker volume create "${redis_volume}" >/dev/null

docker run -d --name "${pg_container}" --network "${network}" \
  -e POSTGRES_DB="${database}" \
  -e POSTGRES_USER=techflow_recovery \
  -e POSTGRES_PASSWORD="${drill_password}" \
  -v "${pg_volume}:/var/lib/postgresql/data" \
  "${postgres_image}" >/dev/null

for _ in $(seq 1 60); do
  if docker exec "${pg_container}" psql \
    -U techflow_recovery -d "${database}" -Atc 'select 1;' >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
docker exec "${pg_container}" psql \
  -U techflow_recovery -d "${database}" -Atc 'select 1;' >/dev/null
docker exec -i "${pg_container}" pg_restore \
  -U techflow_recovery -d "${database}" --no-owner --no-privileges \
  <"${workdir}/postgres.dump"

actual_tables=$(docker exec "${pg_container}" psql \
  -U techflow_recovery -d "${database}" -Atc \
  "select count(*) from information_schema.tables where table_schema='public';")
[[ ${actual_tables} == "${expected_tables}" ]] || {
  echo "PostgreSQL table-count mismatch: expected=${expected_tables} actual=${actual_tables}" >&2
  exit 1
}

docker run --rm \
  -v "${redis_volume}:/data" \
  -v "${workdir}:/backup:ro" \
  --entrypoint sh "${redis_image}" \
  -c 'cp /backup/redis.rdb /data/dump.rdb && chown redis:redis /data/dump.rdb'
docker run --rm \
  -v "${workdir}:/backup:ro" \
  --entrypoint redis-check-rdb "${redis_image}" \
  /backup/redis.rdb >/dev/null
docker run -d --name "${redis_container}" --network "${network}" \
  -v "${redis_volume}:/data" \
  "${redis_image}" redis-server --appendonly no --requirepass "${drill_password}" >/dev/null

for _ in $(seq 1 60); do
  if docker exec -e REDISCLI_AUTH="${drill_password}" "${redis_container}" \
    redis-cli ping 2>/dev/null | grep -q PONG; then
    break
  fi
  sleep 1
done
actual_redis_keys=$(docker exec -e REDISCLI_AUTH="${drill_password}" \
  "${redis_container}" redis-cli --raw DBSIZE)

probe_postgres=not-requested
probe_redis=not-requested
if [[ -n ${probe_id} ]]; then
  probe_postgres=$(docker exec "${pg_container}" psql \
    -U techflow_recovery -d "${database}" -Atc \
    "select count(*) from techflow_recovery_probe where probe_id='${probe_id}';")
  [[ ${probe_postgres} == "1" ]] || {
    echo "PostgreSQL recovery probe is missing." >&2
    exit 1
  }
  probe_redis=$(docker exec -e REDISCLI_AUTH="${drill_password}" \
    "${redis_container}" redis-cli --raw GET techflow:recovery:probe)
  [[ ${probe_redis} == "${probe_id}" ]] || {
    echo "Redis recovery probe is missing." >&2
    exit 1
  }
  probe_postgres=pass
  probe_redis=pass
fi

duration=$(( $(date +%s) - started_epoch ))
completed_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
if [[ -n ${evidence_output} ]]; then
  install -d -m 0750 -o root -g ablecloud "$(dirname -- "${evidence_output}")"
  python3 - "${evidence_output}" "${completed_at}" "${archive}" "${duration}" \
    "${actual_tables}" "${source_observed_redis_keys}" "${actual_redis_keys}" \
    "${probe_postgres}" "${probe_redis}" <<'PY'
import json
import os
import sys
from pathlib import Path

(
    output,
    completed,
    archive,
    duration,
    tables,
    source_keys,
    restored_keys,
    pg_probe,
    redis_probe,
) = sys.argv[1:]
payload = {
    "schemaVersion": "1.0",
    "issue": 16,
    "completedAt": completed,
    "archive": Path(archive).name,
    "isolated": True,
    "publishedPorts": 0,
    "productionRestarted": False,
    "restoreDurationSeconds": int(duration),
    "postgres": {"status": "PASS", "publicTableCount": int(tables), "probe": pg_probe},
    "redis": {
        "status": "PASS",
        "sourceObservedKeyCount": int(source_keys),
        "restoredKeyCount": int(restored_keys),
        "rdbIntegrity": "PASS",
        "probe": redis_probe,
    },
    "cleanupPolicy": "temporary containers, network, volumes and plaintext files removed",
    "containsRuntimeSecrets": False,
}
path = Path(output)
path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
os.chmod(path, 0o640)
PY
  chown root:ablecloud "${evidence_output}"
fi

succeeded=true
echo "restore=passed isolated=true published_ports=0 postgres_tables=${actual_tables} redis_keys=${actual_redis_keys} duration_seconds=${duration} cleanup=scheduled"
