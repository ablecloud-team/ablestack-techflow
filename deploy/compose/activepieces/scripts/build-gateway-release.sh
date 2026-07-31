#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
deploy_dir=$(cd -- "${script_dir}/.." && pwd)
lock_file=${1:-${deploy_dir}/image-lock.json}

cd "${deploy_dir}"
lock_file=$(realpath -- "${lock_file}")
python3 scripts/release_lock.py validate --lock "${lock_file}" --allow-pending

readarray -t gateway_lock < <(python3 - "${lock_file}" <<'PY'
import json
import sys
data = json.load(open(sys.argv[1], encoding="utf-8"))["services"]["event-gateway"]
print(data["imageRef"])
print(data["version"])
print(data["expectedImageId"])
PY
)

docker build --pull=false --provenance=false \
  --build-arg "TECHFLOW_GATEWAY_VERSION=${gateway_lock[1]}" \
  --build-arg SOURCE_DATE_EPOCH=0 \
  --tag "${gateway_lock[0]}" \
  event-gateway

image_id=$(docker image inspect --format '{{.Id}}' "${gateway_lock[0]}")
if [[ ${gateway_lock[2]} != "PENDING_SERVER_BUILD" && ${image_id} != "${gateway_lock[2]}" ]]; then
  echo "Built image does not match expectedImageId. Create a new reviewed release lock." >&2
  exit 1
fi

echo "gateway_image=${gateway_lock[0]} image_id=${image_id}"
