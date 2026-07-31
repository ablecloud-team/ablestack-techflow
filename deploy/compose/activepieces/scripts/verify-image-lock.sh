#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
deploy_dir=$(cd -- "${script_dir}/.." && pwd)
lock_file=${1:-${deploy_dir}/image-lock.json}

cd "${deploy_dir}"
lock_file=$(realpath -- "${lock_file}")
python3 -m unittest -v scripts/test_release_lock.py
python3 scripts/release_lock.py validate \
  --lock "${lock_file}" \
  --compose compose.yml \
  --dockerfile event-gateway/Dockerfile

release_env=$(mktemp)
trap 'rm -f -- "${release_env}"' EXIT
python3 scripts/release_lock.py env --lock "${lock_file}" --output "${release_env}" >/dev/null
docker compose --env-file .env --env-file "${release_env}" config --quiet
python3 scripts/release_lock.py verify-running --lock "${lock_file}"
./scripts/healthcheck.sh --wait 120

scan_target=$(mktemp -d)
trap 'rm -rf -- "${scan_target}" "${release_env}"' EXIT
cp -a image-lock.json scripts/release_lock.py scripts/deploy-locked.sh \
  scripts/build-gateway-release.sh scripts/rollback-release.sh \
  scripts/verify-image-lock.sh scripts/test-image-release.sh \
  "${scan_target}/"
if [[ -d /var/lib/ablestack-techflow/releases ]]; then
  cp -a /var/lib/ablestack-techflow/releases "${scan_target}/runtime"
fi
python3 scripts/secret_scan.py --env-file .env --scan-root "${scan_target}"

echo "image_lock=verified services=6 health=passed secret_scan=passed"
