#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
deploy_dir=$(cd -- "${script_dir}/.." && pwd)
source_file="${deploy_dir}/.env.example"
target_file="${deploy_dir}/.env"

if [[ -e ${target_file} && ${1:-} != "--force" ]]; then
  echo "${target_file} already exists. Use --force only when secret rotation is intended." >&2
  exit 1
fi

command -v openssl >/dev/null
umask 077
cp "${source_file}" "${target_file}"

replace_value() {
  local key=$1
  local value=$2
  sed -i "s|^${key}=.*$|${key}=${value}|" "${target_file}"
}

replace_value AP_API_KEY "$(openssl rand -hex 64)"
replace_value AP_ENCRYPTION_KEY "$(openssl rand -hex 16)"
replace_value AP_JWT_SECRET "$(openssl rand -hex 32)"
replace_value AP_POSTGRES_PASSWORD "$(openssl rand -hex 32)"
replace_value AP_REDIS_PASSWORD "$(openssl rand -hex 32)"
replace_value TECHFLOW_WEBHOOK_SECRET "$(openssl rand -hex 32)"
replace_value TECHFLOW_WEBHOOK_SECRET_PREVIOUS ""
replace_value TECHFLOW_GITHUB_WEBHOOK_SECRET "$(openssl rand -hex 32)"
replace_value TECHFLOW_CHAT_WEBHOOK_URL ""

if [[ -n ${TF_AP_BIND_ADDRESS:-} ]]; then
  replace_value AP_BIND_ADDRESS "${TF_AP_BIND_ADDRESS}"
fi
if [[ -n ${TF_AP_FRONTEND_URL:-} ]]; then
  replace_value AP_FRONTEND_URL "${TF_AP_FRONTEND_URL}"
fi

chmod 600 "${target_file}"
echo "Created ${target_file} with mode 0600. Secret values were not printed."
