#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
deploy_dir=$(cd -- "${script_dir}/.." && pwd)

cd "${deploy_dir}"
set -a
source .env
set +a

http_url=${TECHFLOW_PUBLIC_URL/https:\/\//http://}
redirect_headers=$(mktemp)
trap 'rm -f "${redirect_headers}"' EXIT

http_status=$(curl --silent --show-error --head \
  --output "${redirect_headers}" --write-out '%{http_code}' "${http_url}/")
location=$(awk 'BEGIN {IGNORECASE=1} /^location:/ {gsub(/\r/, "", $2); print $2}' "${redirect_headers}")
case "${http_status}" in
  301|302|307|308) ;;
  *)
    echo "HTTP redirect failed: status=${http_status}" >&2
    exit 1
    ;;
esac
if [[ ${location} != https://* ]]; then
  echo "HTTP redirect failed: HTTPS Location header is missing" >&2
  exit 1
fi

https_status=$(curl --silent --show-error --output /dev/null \
  --write-out '%{http_code}' "${TECHFLOW_PUBLIC_URL}/api/v1/health")
if [[ ${https_status} != "200" ]]; then
  echo "HTTPS health failed: status=${https_status}" >&2
  exit 1
fi

"${script_dir}/verify-webhook.sh" "${TECHFLOW_PUBLIC_URL}"
echo "ingress http_redirect=${http_status} https_health=${https_status} tls_verify=pass"
