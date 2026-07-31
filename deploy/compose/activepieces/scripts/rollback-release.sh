#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
deploy_dir=$(cd -- "${script_dir}/.." && pwd)
lock_file=${1:?Usage: rollback-release.sh RUNTIME_LOCK.json}
release_dir=${TECHFLOW_RELEASE_DIR:-/var/lib/ablestack-techflow/releases}

if [[ ${EUID} -ne 0 ]]; then
  echo "Run this command with sudo." >&2
  exit 1
fi

lock_file=$(realpath -- "${lock_file}")
cd "${deploy_dir}"
python3 scripts/release_lock.py validate --lock "${lock_file}"

release_env=$(mktemp /run/techflow-rollback.XXXXXX.env)
trap 'rm -f -- "${release_env}"' EXIT
python3 scripts/release_lock.py env --lock "${lock_file}" --output "${release_env}" >/dev/null

python3 - "${lock_file}" <<'PY' | while IFS= read -r image_ref; do
import json
import sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
for item in data["services"].values():
    print(item["imageRef"])
PY
  docker image inspect "${image_ref}" >/dev/null || {
    echo "Rollback image is not available locally." >&2
    exit 1
  }
done

docker compose --env-file .env --env-file "${release_env}" up -d --no-build --remove-orphans
./scripts/healthcheck.sh --wait 300
python3 scripts/release_lock.py verify-running --lock "${lock_file}"
/usr/local/libexec/techflow-observer collect --strict >/dev/null

install -d -m 0750 -o root -g ablecloud "${release_dir}"
release_id=$(python3 - "${lock_file}" <<'PY'
import json
import sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["releaseId"])
PY
)
python3 scripts/release_lock.py capture \
  --release-id "rollback-${release_id}" \
  --output "${release_dir}/runtime-lock.current.json" >/dev/null

echo "rollback=${release_id} images=local-only health=passed"
