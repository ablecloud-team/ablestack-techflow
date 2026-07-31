#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
passphrase_file=$(mktemp /run/techflow-secret-escrow-pass.XXXXXX)
output_dir=$(mktemp -d /var/tmp/techflow-secret-escrow-test.XXXXXX)
bundle=

cleanup() {
  if [[ -f ${passphrase_file} ]]; then
    shred -u -- "${passphrase_file}" 2>/dev/null || rm -f -- "${passphrase_file}"
  fi
  rm -rf -- "${output_dir}"
}
trap cleanup EXIT

chmod 0600 "${passphrase_file}"
chown root:root "${passphrase_file}"
openssl rand -hex 32 >"${passphrase_file}"

output=$("${script_dir}/backup-secret-store.sh" \
  --passphrase-file "${passphrase_file}" \
  --output-dir "${output_dir}" \
  --label recovery-drill)
bundle=$(printf '%s\n' "${output}" | tail -n 1)
"${script_dir}/restore-secret-store-drill.sh" \
  --bundle "${bundle}" \
  --passphrase-file "${passphrase_file}"

echo "secret_escrow_drill=passed encrypted_bundle=temporary passphrase=temporary production_store=unchanged"
