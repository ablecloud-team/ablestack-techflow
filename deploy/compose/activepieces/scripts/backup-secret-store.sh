#!/usr/bin/env bash

set -euo pipefail

source_file=${TECHFLOW_SECRET_STORE:-/etc/ablestack-techflow/secrets/activepieces.env}
output_dir=${TECHFLOW_SECRET_ESCROW_DIR:-/var/backups/ablestack-techflow/secret-escrow}
passphrase_file=
label=manual

usage() {
  echo "Usage: $0 --passphrase-file PATH [--output-dir PATH] [--label NAME]"
}

while (($#)); do
  case "$1" in
    --passphrase-file)
      passphrase_file=${2:?missing passphrase file}
      shift 2
      ;;
    --output-dir)
      output_dir=${2:?missing output directory}
      shift 2
      ;;
    --label)
      label=${2:?missing label}
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
done

[[ ${EUID} -eq 0 ]] || {
  echo "Secret escrow backup requires root." >&2
  exit 1
}
[[ -f ${source_file} && ! -L ${source_file} ]] || {
  echo "Protected secret store is missing or is a symbolic link." >&2
  exit 1
}
[[ -n ${passphrase_file} && -f ${passphrase_file} && ! -L ${passphrase_file} ]] || {
  echo "A regular passphrase file is required." >&2
  exit 1
}
[[ $(stat -c %U "${passphrase_file}") == root && $(stat -c %a "${passphrase_file}") == 600 ]] || {
  echo "Passphrase file must be root-owned with mode 0600." >&2
  exit 1
}
[[ ${label} =~ ^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$ ]] || {
  echo "Invalid escrow label." >&2
  exit 2
}

umask 077
install -d -m 0700 -o root -g root "${output_dir}"
stamp=$(date -u +%Y%m%dT%H%M%SZ)
created_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
bundle="${output_dir}/techflow-secret-escrow-${stamp}-${label}.gpg"
metadata="${bundle}.json"
temporary="${bundle}.partial"
trap 'rm -f -- "${temporary}"' EXIT

gpg --batch --yes --quiet --pinentry-mode loopback \
  --passphrase-file "${passphrase_file}" \
  --symmetric --cipher-algo AES256 --s2k-digest-algo SHA512 \
  --s2k-count 65011712 --compress-algo none \
  --output "${temporary}" "${source_file}"
mv -- "${temporary}" "${bundle}"
chmod 0600 "${bundle}"

python3 - "${metadata}" "${created_at}" "${bundle}" <<'PY'
import hashlib
import json
import os
import sys
from pathlib import Path

output, created, bundle_name = sys.argv[1:]
bundle = Path(bundle_name)
payload = {
    "schemaVersion": "1.0",
    "createdAt": created,
    "cipher": "OpenPGP symmetric AES256 with integrity protection",
    "bundle": bundle.name,
    "bytes": bundle.stat().st_size,
    "sha256": hashlib.sha256(bundle.read_bytes()).hexdigest(),
    "passphraseStoredWithBundle": False,
    "containsPlaintextSecret": False,
}
path = Path(output)
path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
os.chmod(path, 0o600)
PY

echo "secret_escrow=created bundle=${bundle} passphrase_separate=true plaintext_retained=false"
echo "${bundle}"
