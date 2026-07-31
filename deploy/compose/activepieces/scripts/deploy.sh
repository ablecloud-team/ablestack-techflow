#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
deploy_dir=$(cd -- "${script_dir}/.." && pwd)

cd "${deploy_dir}"

command -v docker >/dev/null
docker compose version >/dev/null

if [[ ! -f .env ]]; then
  echo "Missing ${deploy_dir}/.env. Run scripts/init-env.sh first." >&2
  exit 1
fi

env_mode=$(stat -Lc '%a' .env)
if [[ ${env_mode} != "600" && ${env_mode} != "640" ]]; then
  echo "${deploy_dir}/.env target must have mode 0600 or 0640." >&2
  exit 1
fi

docker compose --env-file .env config --quiet
docker compose --env-file .env pull
docker compose --env-file .env up -d --build --remove-orphans
"${script_dir}/healthcheck.sh" --wait 300

echo "Activepieces Compose deployment is healthy."
