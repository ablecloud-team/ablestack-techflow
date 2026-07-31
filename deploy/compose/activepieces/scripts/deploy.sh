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

if [[ $(stat -c '%a' .env) != "600" ]]; then
  echo "${deploy_dir}/.env must have mode 0600." >&2
  exit 1
fi

docker compose --env-file .env config --quiet
docker compose --env-file .env pull
docker compose --env-file .env up -d --build --remove-orphans
"${script_dir}/healthcheck.sh" --wait 300

echo "Activepieces Compose deployment is healthy."
