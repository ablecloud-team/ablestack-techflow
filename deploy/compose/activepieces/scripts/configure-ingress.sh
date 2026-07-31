#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
deploy_dir=$(cd -- "${script_dir}/.." && pwd)
env_file="${deploy_dir}/.env"
public_url=${1:-https://techflow.ablecloud.io}

if [[ ! -f ${env_file} ]]; then
  echo "Missing ${env_file}. Run scripts/init-env.sh first." >&2
  exit 1
fi
if [[ ${public_url} != https://* ]]; then
  echo "The public URL must use HTTPS." >&2
  exit 1
fi

command -v openssl >/dev/null
umask 077

set_value() {
  local key=$1
  local value=$2
  if grep -q "^${key}=" "${env_file}"; then
    sed -i "s|^${key}=.*$|${key}=${value}|" "${env_file}"
  else
    printf '%s=%s\n' "${key}" "${value}" >>"${env_file}"
  fi
}

set_default() {
  local key=$1
  local value=$2
  if ! grep -q "^${key}=" "${env_file}"; then
    printf '%s=%s\n' "${key}" "${value}" >>"${env_file}"
  fi
}

set_value AP_FRONTEND_URL "${public_url%/}"
set_value TECHFLOW_PUBLIC_URL "${public_url%/}"

if ! grep -q '^TECHFLOW_WEBHOOK_SECRET=.\+' "${env_file}"; then
  set_value TECHFLOW_WEBHOOK_SECRET "$(openssl rand -hex 32)"
fi
if ! grep -q '^TECHFLOW_GITHUB_WEBHOOK_SECRET=.\+' "${env_file}"; then
  set_value TECHFLOW_GITHUB_WEBHOOK_SECRET "$(openssl rand -hex 32)"
fi

set_default TECHFLOW_WEBHOOK_LISTEN_HOST "0.0.0.0"
set_default TECHFLOW_WEBHOOK_LISTEN_PORT "8081"
set_default TECHFLOW_WEBHOOK_PATH_PREFIX "/techflow/hooks/"
set_default TECHFLOW_WEBHOOK_MAX_SKEW_SECONDS "300"
set_default TECHFLOW_WEBHOOK_EVENT_TTL_SECONDS "86400"
set_default TECHFLOW_WEBHOOK_BODY_LIMIT_BYTES "1048576"
set_default TECHFLOW_WEBHOOK_UPSTREAM_URL ""
set_default TECHFLOW_WEBHOOK_SECRET_PREVIOUS ""
set_default TECHFLOW_GITHUB_WEBHOOK_PATH "/techflow/hooks/github/chat"
set_default TECHFLOW_GITHUB_ORGANIZATION "ablecloud-team"
set_default TECHFLOW_GITHUB_EVENT_TTL_SECONDS "604800"
set_default TECHFLOW_GITHUB_UPSTREAM_URL ""
set_default TECHFLOW_CHAT_INTERNAL_PATH "/internal/chat/github"
set_default TECHFLOW_CHAT_TIMEOUT_SECONDS "10"
set_default TECHFLOW_CHAT_MIN_INTERVAL_MILLISECONDS "600"
set_default TECHFLOW_CHAT_WEBHOOK_URL ""
set_default AP_SSRF_ALLOW_LIST "172.30.19.9,172.30.19.10"

if [[ -w ${env_file} ]]; then
  chmod 600 "${env_file}"
fi
echo "Configured canonical HTTPS URL and signed Webhook settings. Secret values were not printed."
