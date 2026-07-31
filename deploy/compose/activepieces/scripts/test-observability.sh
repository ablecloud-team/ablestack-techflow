#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
deploy_dir=$(cd -- "${script_dir}/.." && pwd)
drill_id=${1:-issue-17}
drill_dir=/var/log/ablestack-techflow/observability/drills

[[ ${drill_id} =~ ^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$ ]] || {
  echo "Invalid drill ID." >&2
  exit 2
}

if [[ ${EUID} -ne 0 ]]; then
  echo "Run this command with sudo." >&2
  exit 1
fi

cd "${deploy_dir}"
set -a
source .env
set +a

gateway_id=$(docker compose --env-file .env ps -q event-gateway)
[[ -n ${gateway_id} ]] || {
  echo "event-gateway container is missing." >&2
  exit 1
}

restore_gateway() {
  docker start "${gateway_id}" >/dev/null 2>&1 || true
  scripts/healthcheck.sh --wait 180 >/dev/null 2>&1 || true
}
trap restore_gateway EXIT

python3 observability/observer.py collect --strict >/dev/null
started_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
docker stop --time 5 "${gateway_id}" >/dev/null
set +e
python3 observability/observer.py collect --strict --drill-id "${drill_id}" >/tmp/techflow-observer-drill.out
failure_exit=$?
set -e
if [[ ${failure_exit} -ne 2 ]]; then
  echo "Observer did not return the expected critical exit code." >&2
  exit 1
fi
grep -q '"key": "service_event-gateway"' /var/lib/ablestack-techflow/observability/current-alerts.json
grep -q '"key": "endpoint_internal_gateway"' /var/lib/ablestack-techflow/observability/current-alerts.json

docker start "${gateway_id}" >/dev/null
scripts/healthcheck.sh --wait 180 >/dev/null
python3 observability/observer.py collect --strict --drill-id "${drill_id}" >/dev/null
python3 observability/observer.py status >/dev/null
python3 - "${drill_id}" /var/log/ablestack-techflow/observability/alerts.jsonl <<'PY'
import json
import sys

drill_id, path = sys.argv[1:]
records = []
with open(path, encoding="utf-8") as stream:
    for line in stream:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            pass
for transition in ("opened", "resolved"):
    if not any(
        item.get("drill_id") == drill_id
        and item.get("key") == "service_event-gateway"
        and item.get("transition") == transition
        for item in records
    ):
        raise SystemExit(f"missing {transition} transition")
PY

ended_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
install -d -m 0750 -o root -g ablecloud "${drill_dir}"
python3 - "${drill_dir}/${drill_id}.json" "${drill_id}" "${started_at}" "${ended_at}" "${failure_exit}" <<'PY'
import json
import os
import sys
import tempfile

path, drill_id, started_at, ended_at, failure_exit = sys.argv[1:]
record = {
    "schema_version": 1,
    "drill_id": drill_id,
    "started_at": started_at,
    "ended_at": ended_at,
    "scenario": "event_gateway_stop_start",
    "expected_exit_code": 2,
    "observed_exit_code": int(failure_exit),
    "alerts_opened": ["endpoint_internal_gateway", "service_event-gateway"],
    "alerts_resolved": ["endpoint_internal_gateway", "service_event-gateway"],
    "post_recovery_health": "passed",
    "payload_or_identifier_recorded": False,
}
fd, temp_name = tempfile.mkstemp(prefix=".drill.", dir=os.path.dirname(path), text=True)
with os.fdopen(fd, "w", encoding="utf-8") as stream:
    json.dump(record, stream, indent=2, sort_keys=True)
    stream.write("\n")
os.chmod(temp_name, 0o640)
os.replace(temp_name, path)
PY

trap - EXIT
echo "drill=${drill_id} detection=passed root_cause=event-gateway recovery=passed"
