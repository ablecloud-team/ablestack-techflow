#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
deploy_dir=$(cd -- "${script_dir}/.." && pwd)

cd "${deploy_dir}"

if [[ ${1:-} == "--purge-data" ]]; then
  if [[ ${CONFIRM_TECHFLOW_DATA_PURGE:-} != "DELETE" ]]; then
    echo "Set CONFIRM_TECHFLOW_DATA_PURGE=DELETE to remove persistent volumes." >&2
    exit 1
  fi
  docker compose --env-file .env down --volumes --remove-orphans
  echo "Containers, networks and persistent volumes were removed."
  exit 0
fi

docker compose --env-file .env down --remove-orphans
echo "Containers and networks were removed. Persistent volumes were preserved."
