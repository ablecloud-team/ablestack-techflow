#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
deploy_dir=$(cd -- "${script_dir}/.." && pwd)
lock_file=${1:-${deploy_dir}/image-lock.json}
release_dir=${TECHFLOW_RELEASE_DIR:-/var/lib/ablestack-techflow/releases}

if [[ ${EUID} -ne 0 ]]; then
  echo "Run this command with sudo." >&2
  exit 1
fi

lock_file=$(realpath -- "${lock_file}")
cd "${deploy_dir}"
test -f .env
python3 scripts/release_lock.py validate \
  --lock "${lock_file}" \
  --compose compose.yml \
  --dockerfile event-gateway/Dockerfile

install -d -m 0750 -o root -g ablecloud "${release_dir}" "${release_dir}/history"
release_env=$(mktemp /run/techflow-release.XXXXXX.env)
trap 'rm -f -- "${release_env}"' EXIT
python3 scripts/release_lock.py env --lock "${lock_file}" --output "${release_env}" >/dev/null

stamp=$(date -u +%Y%m%dT%H%M%SZ)
python3 scripts/release_lock.py capture \
  --release-id "pre-deploy-${stamp}" \
  --output "${release_dir}/runtime-lock.previous.json" >/dev/null
./scripts/backup-state.sh --label "pre-release-${stamp}" --retention-days 7 >/dev/null

docker compose --env-file .env --env-file "${release_env}" pull postgres redis app worker ingress

readarray -t gateway_lock < <(python3 - "${lock_file}" <<'PY'
import json
import sys
data = json.load(open(sys.argv[1], encoding="utf-8"))["services"]["event-gateway"]
print(data["imageRef"])
print(data["expectedImageId"])
PY
)
gateway_id=$(docker image inspect --format '{{.Id}}' "${gateway_lock[0]}")
if [[ ${gateway_id} != "${gateway_lock[1]}" ]]; then
  echo "Gateway build does not match the release lock." >&2
  exit 1
fi

docker compose --env-file .env --env-file "${release_env}" up -d --no-build --remove-orphans
./scripts/healthcheck.sh --wait 300
python3 scripts/release_lock.py verify-running --lock "${lock_file}"
/usr/local/libexec/techflow-observer collect --strict >/dev/null

release_id=$(python3 - "${lock_file}" <<'PY'
import json
import sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["releaseId"])
PY
)
python3 scripts/release_lock.py capture \
  --release-id "${release_id}-runtime" \
  --output "${release_dir}/runtime-lock.current.json" >/dev/null
install -m 0640 -o root -g ablecloud "${lock_file}" "${release_dir}/history/${stamp}-${release_id}.json"

find "${release_dir}/history" -maxdepth 1 -type f -name '*.json' -printf '%T@ %p\n' \
  | sort -rn | awk 'NR > 10 {sub(/^[^ ]+ /, ""); print}' \
  | while IFS= read -r old_lock; do rm -f -- "${old_lock}"; done

echo "release=${release_id} deployment=healthy digests=verified backup=created"
