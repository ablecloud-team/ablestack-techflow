#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
deploy_dir=$(cd -- "${script_dir}/.." && pwd)
env_file=$(readlink -f "${deploy_dir}/.env")

if [[ ! -f ${env_file} ]]; then
  echo "Runtime secret file is missing." >&2
  exit 1
fi

mode=$(stat -c '%a' "${env_file}")
if [[ ${mode} != "600" && ${mode} != "640" ]]; then
  echo "Runtime secret file mode must be 0600 or 0640." >&2
  exit 1
fi

python3 "${script_dir}/secret_env.py" inventory --file "${env_file}" \
  AP_API_KEY \
  AP_ENCRYPTION_KEY \
  AP_JWT_SECRET \
  AP_POSTGRES_PASSWORD \
  AP_REDIS_PASSWORD \
  TECHFLOW_WEBHOOK_SECRET \
  TECHFLOW_WEBHOOK_SECRET_PREVIOUS

python3 "${script_dir}/secret_scan.py" \
  --env-file "${env_file}" \
  --scan-root "${deploy_dir}"

cd "${deploy_dir}"
docker compose --env-file .env logs --no-color 2>&1 |
  python3 "${script_dir}/secret_scan.py" \
    --env-file "${env_file}" \
    --stdin-label docker-logs

echo "secret_storage=valid secret_exposure=none"
