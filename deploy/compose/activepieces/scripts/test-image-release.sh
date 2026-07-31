#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
deploy_dir=$(cd -- "${script_dir}/.." && pwd)
lock_file=${1:-${deploy_dir}/image-lock.json}
release_dir=${TECHFLOW_RELEASE_DIR:-/var/lib/ablestack-techflow/releases}
drill_dir=/var/log/ablestack-techflow/release-drills
drill_id=${2:-issue-18-image-lock}

if [[ ${EUID} -ne 0 ]]; then
  echo "Run this command with sudo." >&2
  exit 1
fi
[[ ${drill_id} =~ ^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$ ]] || exit 2

cd "${deploy_dir}"
lock_file=$(realpath -- "${lock_file}")
install -d -m 0750 -o root -g ablecloud "${release_dir}" "${drill_dir}"
baseline="${release_dir}/${drill_id}-baseline.json"
first="${release_dir}/${drill_id}-first.json"
second="${release_dir}/${drill_id}-second.json"
final="${release_dir}/${drill_id}-final.json"

volume_before=$(docker volume ls --filter name=techflow-activepieces --format '{{.Name}}' | sort | tr '\n' ',')
python3 scripts/release_lock.py capture --release-id "${drill_id}-baseline" --output "${baseline}" >/dev/null

./scripts/deploy-locked.sh "${lock_file}" >/dev/null
python3 scripts/release_lock.py capture --release-id "${drill_id}-first" --output "${first}" >/dev/null

release_env=$(mktemp /run/techflow-repeat.XXXXXX.env)
trap 'rm -f -- "${release_env}"' EXIT
python3 scripts/release_lock.py env --lock "${lock_file}" --output "${release_env}" >/dev/null
docker compose --env-file .env --env-file "${release_env}" up -d --no-build --remove-orphans >/dev/null
./scripts/healthcheck.sh --wait 180 >/dev/null
python3 scripts/release_lock.py capture --release-id "${drill_id}-second" --output "${second}" >/dev/null
python3 scripts/release_lock.py compare --first "${first}" --second "${second}" >/dev/null

./scripts/rollback-release.sh "${baseline}" >/dev/null
python3 scripts/release_lock.py verify-running --lock "${baseline}" >/dev/null

./scripts/deploy-locked.sh "${lock_file}" >/dev/null
python3 scripts/release_lock.py capture --release-id "${drill_id}-final" --output "${final}" >/dev/null
python3 scripts/release_lock.py compare --first "${first}" --second "${final}" >/dev/null

volume_after=$(docker volume ls --filter name=techflow-activepieces --format '{{.Name}}' | sort | tr '\n' ',')
[[ ${volume_before} == "${volume_after}" ]]
./scripts/healthcheck.sh --wait 180 >/dev/null
python3 scripts/release_lock.py verify-running --lock "${lock_file}" >/dev/null

python3 - "${drill_dir}/${drill_id}.json" "${drill_id}" <<'PY'
import datetime as dt
import json
import os
import sys
import tempfile
path, drill_id = sys.argv[1:]
record = {
    "schemaVersion": "1.0",
    "drillId": drill_id,
    "completedAt": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "scenario": "tag-only-to-digest-lock-with-local-rollback",
    "firstAndRepeatedImagesIdentical": True,
    "rollbackUsedLocalImagesOnly": True,
    "rollbackHealth": "PASS",
    "finalLockedReleaseHealth": "PASS",
    "persistentVolumeNamesUnchanged": True,
    "secretsOrPayloadsRecorded": False,
}
fd, temp_name = tempfile.mkstemp(prefix=".release-drill.", dir=os.path.dirname(path), text=True)
with os.fdopen(fd, "w", encoding="utf-8") as stream:
    json.dump(record, stream, indent=2, sort_keys=True)
    stream.write("\n")
os.chmod(temp_name, 0o640)
os.replace(temp_name, path)
PY

trap - EXIT
rm -f -- "${release_env}"
echo "drill=${drill_id} repeat=identical rollback=passed final=locked volumes=unchanged"
