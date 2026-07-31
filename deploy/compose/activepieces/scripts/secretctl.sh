#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
deploy_dir=$(cd -- "${script_dir}/.." && pwd)
secret_root=${TECHFLOW_SECRET_ROOT:-/etc/ablestack-techflow/secrets}
secret_file="${secret_root}/activepieces.env"
audit_root=${TECHFLOW_SECRET_AUDIT_ROOT:-/var/log/ablestack-techflow}
audit_file="${audit_root}/secret-audit.jsonl"
secret_group=${TECHFLOW_SECRET_GROUP:-ablecloud}
env_link="${deploy_dir}/.env"

usage() {
  cat <<'EOF'
Usage:
  sudo ./scripts/secretctl.sh bootstrap
  ./scripts/secretctl.sh status
  sudo ./scripts/secretctl.sh prepare-webhook-rotation
  sudo ./scripts/secretctl.sh revoke-previous-webhook
  sudo ./scripts/secretctl.sh rollback-webhook-rotation
  sudo ./scripts/secretctl.sh test-webhook-rotation [base-url]

Secret values are never printed. Mutating commands require root.
EOF
}

require_root() {
  if [[ ${EUID} -ne 0 ]]; then
    echo "This command must be run with sudo." >&2
    exit 1
  fi
}

require_secret_file() {
  if [[ ! -f ${secret_file} ]]; then
    echo "Secret store is not initialized. Run bootstrap first." >&2
    exit 1
  fi
}

audit() {
  local action=$1
  local target=$2
  local result=$3
  local actor=${SUDO_USER:-$(id -un)}
  install -d -m 0750 -o root -g "${secret_group}" "${audit_root}"
  touch "${audit_file}"
  chown root:"${secret_group}" "${audit_file}"
  chmod 0640 "${audit_file}"
  python3 - "${audit_file}" "${actor}" "${action}" "${target}" "${result}" <<'PY'
import datetime
import json
import sys

path, actor, action, target, result = sys.argv[1:]
record = {
    "time": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
    "actor": actor,
    "action": action,
    "target": target,
    "result": result,
}
with open(path, "a", encoding="utf-8") as stream:
    stream.write(json.dumps(record, separators=(",", ":")) + "\n")
PY
}

set_secret() {
  local key=$1
  local value=$2
  printf '%s' "${value}" |
    python3 "${script_dir}/secret_env.py" set \
      --file "${secret_file}" \
      --key "${key}" \
      --value-stdin
}

load_secrets() {
  set -a
  # shellcheck disable=SC1090
  source "${secret_file}"
  set +a
}

restart_gateway() {
  cd "${deploy_dir}"
  docker compose --env-file .env up -d --no-deps --build --force-recreate event-gateway
  "${script_dir}/healthcheck.sh" --wait 300 >/dev/null
}

prepare_webhook_rotation() {
  require_root
  require_secret_file
  load_secrets
  if [[ -z ${TECHFLOW_WEBHOOK_SECRET:-} ]]; then
    echo "Current Webhook Secret is missing." >&2
    exit 1
  fi
  if [[ -n ${TECHFLOW_WEBHOOK_SECRET_PREVIOUS:-} ]]; then
    echo "A previous Webhook Secret already exists; revoke or roll back first." >&2
    exit 1
  fi

  local previous=${TECHFLOW_WEBHOOK_SECRET}
  local current
  current=$(openssl rand -hex 32)
  set_secret TECHFLOW_WEBHOOK_SECRET_PREVIOUS "${previous}"
  set_secret TECHFLOW_WEBHOOK_SECRET "${current}"
  restart_gateway
  audit "rotate.prepare" "TECHFLOW_WEBHOOK_SECRET" "success"
  echo "Webhook Secret rotation prepared. Current and previous credentials are accepted."
}

revoke_previous_webhook() {
  require_root
  require_secret_file
  load_secrets
  if [[ -z ${TECHFLOW_WEBHOOK_SECRET_PREVIOUS:-} ]]; then
    echo "Previous Webhook Secret is already empty." >&2
    exit 1
  fi
  set_secret TECHFLOW_WEBHOOK_SECRET_PREVIOUS ""
  restart_gateway
  audit "rotate.revoke_previous" "TECHFLOW_WEBHOOK_SECRET" "success"
  echo "Previous Webhook Secret was revoked."
}

rollback_webhook_rotation() {
  require_root
  require_secret_file
  load_secrets
  if [[ -z ${TECHFLOW_WEBHOOK_SECRET_PREVIOUS:-} ]]; then
    echo "No previous Webhook Secret is available for rollback." >&2
    exit 1
  fi
  local previous=${TECHFLOW_WEBHOOK_SECRET_PREVIOUS}
  set_secret TECHFLOW_WEBHOOK_SECRET "${previous}"
  set_secret TECHFLOW_WEBHOOK_SECRET_PREVIOUS ""
  restart_gateway
  audit "rotate.rollback" "TECHFLOW_WEBHOOK_SECRET" "success"
  echo "Webhook Secret rotation was rolled back."
}

signature() {
  local secret=$1
  local timestamp=$2
  local body=$3
  {
    printf '%s\n' "${secret}"
    printf '%s.%s' "${timestamp}" "${body}"
  } | python3 -c '
import hashlib
import hmac
import sys
secret = sys.stdin.buffer.readline().rstrip(b"\n")
message = sys.stdin.buffer.read()
print("sha256=" + hmac.new(secret, message, hashlib.sha256).hexdigest())
'
}

request() {
  local expected=$1
  local secret=$2
  local url=$3
  local event_id=$4
  local body=$5
  local timestamp
  local supplied
  local actual
  timestamp=$(date +%s)
  supplied=$(signature "${secret}" "${timestamp}" "${body}")
  actual=$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    -X POST "${url}" \
    -H 'Content-Type: application/json' \
    -H "X-TechFlow-Timestamp: ${timestamp}" \
    -H "X-TechFlow-Event-Id: ${event_id}" \
    -H "X-TechFlow-Signature: ${supplied}" \
    --data-binary "${body}")
  if [[ ${actual} != "${expected}" ]]; then
    echo "Webhook lifecycle verification failed: expected=${expected} actual=${actual}" >&2
    return 1
  fi
}

test_webhook_rotation() {
  require_root
  require_secret_file
  load_secrets
  if [[ -n ${TECHFLOW_WEBHOOK_SECRET_PREVIOUS:-} ]]; then
    echo "Lifecycle test requires an empty previous Webhook Secret." >&2
    exit 1
  fi
  local retired=${TECHFLOW_WEBHOOK_SECRET}
  local base_url=${1:-${TECHFLOW_PUBLIC_URL}}
  local webhook_url="${base_url%/}/techflow/hooks/secret-lifecycle"
  local body='{"probe":"issue-15-secret-lifecycle"}'
  local prefix="issue15-$(date -u +%Y%m%dT%H%M%SZ)-$$"

  prepare_webhook_rotation
  load_secrets
  local current=${TECHFLOW_WEBHOOK_SECRET}
  request 202 "${current}" "${webhook_url}" "${prefix}-current-grace" "${body}"
  request 202 "${retired}" "${webhook_url}" "${prefix}-previous-grace" "${body}"

  revoke_previous_webhook
  load_secrets
  request 202 "${current}" "${webhook_url}" "${prefix}-current-final" "${body}"
  request 401 "${retired}" "${webhook_url}" "${prefix}-retired" "${body}"
  audit "rotate.lifecycle_test" "TECHFLOW_WEBHOOK_SECRET" "success"
  echo "Webhook Secret lifecycle verified: current=202 previous_grace=202 retired=401."
}

bootstrap() {
  require_root
  install -d -m 0750 -o root -g "${secret_group}" "${secret_root}"

  if [[ ! -f ${secret_file} ]]; then
    if [[ ! -f ${env_link} || -L ${env_link} ]]; then
      echo "A regular ${env_link} is required for first migration." >&2
      exit 1
    fi
    local source_mode
    source_mode=$(stat -c '%a' "${env_link}")
    if [[ ${source_mode} != "600" ]]; then
      echo "Source .env must have mode 0600." >&2
      exit 1
    fi
    install -m 0640 -o root -g "${secret_group}" "${env_link}" "${secret_file}"
    if [[ $(sha256sum "${env_link}" | awk '{print $1}') != \
          $(sha256sum "${secret_file}" | awk '{print $1}') ]]; then
      echo "Secret migration checksum mismatch." >&2
      exit 1
    fi
  fi

  chown root:"${secret_group}" "${secret_file}"
  chmod 0640 "${secret_file}"
  python3 "${script_dir}/secret_env.py" inventory --file "${secret_file}" \
    TECHFLOW_WEBHOOK_SECRET_PREVIOUS >/dev/null
  if ! grep -q '^TECHFLOW_WEBHOOK_SECRET_PREVIOUS=' "${secret_file}"; then
    set_secret TECHFLOW_WEBHOOK_SECRET_PREVIOUS ""
  fi

  if [[ -e ${env_link} || -L ${env_link} ]]; then
    rm -f "${env_link}"
  fi
  ln -s "${secret_file}" "${env_link}"
  chown -h root:"${secret_group}" "${env_link}"
  audit "store.bootstrap" "activepieces.env" "success"
  echo "Secret store initialized. Runtime .env is a link to the protected store."
}

status() {
  require_secret_file
  printf 'store=%s\n' "${secret_file}"
  stat -c 'mode=%a owner=%U group=%G' "${secret_file}"
  if [[ -L ${env_link} ]]; then
    printf 'runtime_link=%s\n' "$(readlink "${env_link}")"
  else
    echo "runtime_link=invalid"
    exit 1
  fi
  python3 "${script_dir}/secret_env.py" inventory --file "${secret_file}" \
    AP_API_KEY \
    AP_ENCRYPTION_KEY \
    AP_JWT_SECRET \
    AP_POSTGRES_PASSWORD \
    AP_REDIS_PASSWORD \
    TECHFLOW_WEBHOOK_SECRET \
    TECHFLOW_WEBHOOK_SECRET_PREVIOUS
  if [[ -f ${audit_file} ]]; then
    stat -c 'audit_mode=%a audit_owner=%U audit_group=%G' "${audit_file}"
  else
    echo "audit=missing"
  fi
}

command=${1:-}
case ${command} in
  bootstrap)
    bootstrap
    ;;
  status)
    status
    ;;
  prepare-webhook-rotation)
    prepare_webhook_rotation
    ;;
  revoke-previous-webhook)
    revoke_previous_webhook
    ;;
  rollback-webhook-rotation)
    rollback_webhook_rotation
    ;;
  test-webhook-rotation)
    shift
    test_webhook_rotation "${1:-}"
    ;;
  *)
    usage
    exit 1
    ;;
esac
