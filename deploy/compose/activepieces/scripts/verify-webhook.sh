#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
deploy_dir=$(cd -- "${script_dir}/.." && pwd)

cd "${deploy_dir}"
set -a
source .env
set +a

command -v curl >/dev/null
command -v python3 >/dev/null

base_url=${1:-${TECHFLOW_PUBLIC_URL}}
webhook_url="${base_url%/}/techflow/hooks/test"
body='{"probe":"issue-14-signed-webhook"}'
event_id="issue14-$(date -u +%Y%m%dT%H%M%SZ)-$$"
timestamp=$(date +%s)

sign() {
  local ts=$1
  {
    printf '%s\n' "${TECHFLOW_WEBHOOK_SECRET}"
    printf '%s.%s' "${ts}" "${body}"
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
  shift
  local code
  code=$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' "$@")
  if [[ ${code} != "${expected}" ]]; then
    echo "expected=${expected} actual=${code}" >&2
    return 1
  fi
  printf '%s' "${code}"
}

valid_signature=$(sign "${timestamp}")
accepted=$(request 202 \
  -X POST "${webhook_url}" \
  -H 'Content-Type: application/json' \
  -H "X-TechFlow-Timestamp: ${timestamp}" \
  -H "X-TechFlow-Event-Id: ${event_id}" \
  -H "X-TechFlow-Signature: ${valid_signature}" \
  --data-binary "${body}")

duplicate=$(request 409 \
  -X POST "${webhook_url}" \
  -H 'Content-Type: application/json' \
  -H "X-TechFlow-Timestamp: ${timestamp}" \
  -H "X-TechFlow-Event-Id: ${event_id}" \
  -H "X-TechFlow-Signature: ${valid_signature}" \
  --data-binary "${body}")

invalid=$(request 401 \
  -X POST "${webhook_url}" \
  -H 'Content-Type: application/json' \
  -H "X-TechFlow-Timestamp: ${timestamp}" \
  -H "X-TechFlow-Event-Id: ${event_id}-invalid" \
  -H 'X-TechFlow-Signature: sha256=0000000000000000000000000000000000000000000000000000000000000000' \
  --data-binary "${body}")

stale_timestamp=$((timestamp - TECHFLOW_WEBHOOK_MAX_SKEW_SECONDS - 30))
stale_signature=$(sign "${stale_timestamp}")
stale=$(request 401 \
  -X POST "${webhook_url}" \
  -H 'Content-Type: application/json' \
  -H "X-TechFlow-Timestamp: ${stale_timestamp}" \
  -H "X-TechFlow-Event-Id: ${event_id}-stale" \
  -H "X-TechFlow-Signature: ${stale_signature}" \
  --data-binary "${body}")

missing=$(request 400 \
  -X POST "${webhook_url}" \
  -H 'Content-Type: application/json' \
  --data-binary "${body}")

echo "signed_webhook accepted=${accepted} duplicate=${duplicate} invalid_signature=${invalid} stale=${stale} missing_headers=${missing}"
