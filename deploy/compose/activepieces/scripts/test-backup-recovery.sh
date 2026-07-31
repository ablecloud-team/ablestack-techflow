#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
deploy_dir=$(cd -- "${script_dir}/.." && pwd)
evidence_dir=${TECHFLOW_RECOVERY_EVIDENCE_DIR:-/var/log/ablestack-techflow/recovery-drills}
probe_id="issue16-$(date -u +%Y%m%dT%H%M%SZ)-$(openssl rand -hex 4)"
archive=

cd "${deploy_dir}"
set -a
source .env
set +a

postgres_before=$(docker compose --env-file .env ps -q postgres)
redis_before=$(docker compose --env-file .env ps -q redis)

cleanup_probe() {
  docker compose --env-file .env exec -T postgres \
    psql -U "${AP_POSTGRES_USERNAME}" -d "${AP_POSTGRES_DATABASE}" \
    -v ON_ERROR_STOP=1 -c \
    "drop table if exists techflow_recovery_probe;" >/dev/null 2>&1 || true
  docker compose --env-file .env exec -T redis sh -c \
    'REDISCLI_AUTH="$AP_REDIS_PASSWORD" redis-cli DEL techflow:recovery:probe >/dev/null' \
    >/dev/null 2>&1 || true
}
trap cleanup_probe EXIT

docker compose --env-file .env exec -T postgres \
  psql -U "${AP_POSTGRES_USERNAME}" -d "${AP_POSTGRES_DATABASE}" \
  -v ON_ERROR_STOP=1 -c \
  "create table if not exists techflow_recovery_probe (
     probe_id text primary key,
     created_at timestamptz not null default now()
   );
   insert into techflow_recovery_probe (probe_id) values ('${probe_id}');" >/dev/null
docker compose --env-file .env exec -T redis sh -c \
  'REDISCLI_AUTH="$AP_REDIS_PASSWORD" redis-cli SET techflow:recovery:probe "$1" >/dev/null' \
  sh "${probe_id}"

backup_output=$("${script_dir}/backup-state.sh" \
  --label recovery-drill --retention-days 30 --probe-id "${probe_id}")
archive=$(printf '%s\n' "${backup_output}" | tail -n 1)
cleanup_probe

evidence="${evidence_dir}/issue-16-$(date -u +%Y%m%dT%H%M%SZ).json"
"${script_dir}/restore-state-drill.sh" \
  --archive "${archive}" \
  --evidence-output "${evidence}"

postgres_after=$(docker compose --env-file .env ps -q postgres)
redis_after=$(docker compose --env-file .env ps -q redis)
[[ ${postgres_before} == "${postgres_after}" && ${redis_before} == "${redis_after}" ]] || {
  echo "Production state-store containers changed during the recovery drill." >&2
  exit 1
}

"${script_dir}/healthcheck.sh" --wait 180
python3 - "${evidence}" <<'PY'
import json
import os
import sys
from pathlib import Path

path = Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8"))
payload["productionContainerIdsUnchanged"] = True
payload["productionHealthAfterDrill"] = "PASS"
payload["probeRemovedFromProduction"] = True
path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
os.chmod(path, 0o640)
PY
chown root:ablecloud "${evidence}"

echo "recovery_drill=passed archive=${archive} evidence=${evidence} production_containers=unchanged production_health=pass"
