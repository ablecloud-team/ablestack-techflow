#!/usr/bin/env bash

set -euo pipefail

source_file=${TECHFLOW_SECRET_STORE:-/etc/ablestack-techflow/secrets/activepieces.env}
bundle=
passphrase_file=

usage() {
  echo "Usage: $0 --bundle FILE --passphrase-file PATH"
}

while (($#)); do
  case "$1" in
    --bundle)
      bundle=${2:?missing bundle}
      shift 2
      ;;
    --passphrase-file)
      passphrase_file=${2:?missing passphrase file}
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
  echo "Secret escrow restore drill requires root." >&2
  exit 1
}
[[ -f ${bundle} && ! -L ${bundle} ]] || {
  echo "Encrypted escrow bundle is missing or is a symbolic link." >&2
  exit 1
}
[[ -f ${passphrase_file} && ! -L ${passphrase_file} ]] || {
  echo "A regular passphrase file is required." >&2
  exit 1
}
[[ $(stat -c %U "${passphrase_file}") == root && $(stat -c %a "${passphrase_file}") == 600 ]] || {
  echo "Passphrase file must be root-owned with mode 0600." >&2
  exit 1
}

umask 077
workdir=$(mktemp -d /var/tmp/techflow-secret-restore.XXXXXX)
restored="${workdir}/activepieces.env"
cleanup() {
  if [[ -f ${restored} ]]; then
    shred -u -- "${restored}" 2>/dev/null || rm -f -- "${restored}"
  fi
  rmdir -- "${workdir}" 2>/dev/null || true
}
trap cleanup EXIT

gpg --batch --yes --quiet --pinentry-mode loopback \
  --passphrase-file "${passphrase_file}" \
  --decrypt --output "${restored}" "${bundle}"
chmod 0600 "${restored}"

required=(
  AP_ENCRYPTION_KEY
  AP_JWT_SECRET
  AP_API_KEY
  AP_POSTGRES_PASSWORD
  AP_REDIS_PASSWORD
  TECHFLOW_WEBHOOK_SECRET
)
for name in "${required[@]}"; do
  grep -Eq "^${name}=.+" "${restored}" || {
    echo "Restored escrow is missing required key: ${name}" >&2
    exit 1
  }
done

source_match=not-compared
if [[ -f ${source_file} && ! -L ${source_file} ]]; then
  [[ $(sha256sum "${source_file}" | cut -d' ' -f1) == \
     "$(sha256sum "${restored}" | cut -d' ' -f1)" ]] || {
    echo "Restored secret-store fingerprint does not match the protected source." >&2
    exit 1
  }
  source_match=pass
fi

echo "secret_restore_drill=passed isolated=true required_keys=present source_fingerprint=${source_match} plaintext_cleanup=scheduled"
