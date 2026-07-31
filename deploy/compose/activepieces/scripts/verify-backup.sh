#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
backup_dir=${TECHFLOW_BACKUP_DIR:-/var/backups/ablestack-techflow/state}
archive=$(find "${backup_dir}" -maxdepth 1 -type f \
  -name 'techflow-state-*.tar.gz' -printf '%T@ %p\n' |
  sort -nr | head -n 1 | cut -d' ' -f2-)

[[ -n ${archive} && -f ${archive} ]] || {
  echo "No TechFlow state backup exists." >&2
  exit 1
}
[[ $(stat -c %a "${backup_dir}") == 750 ]] || {
  echo "Backup directory permissions must be 0750." >&2
  exit 1
}
[[ $(stat -c %a "${archive}") == 640 ]] || {
  echo "Backup archive permissions must be 0640." >&2
  exit 1
}
if tar -tzf "${archive}" | grep -Eq '(^|/)(\.env|activepieces\.env|secret-audit\.jsonl)$'; then
  echo "Backup archive contains a forbidden secret-bearing file." >&2
  exit 1
fi

workdir=$(mktemp -d /var/tmp/techflow-backup-verify.XXXXXX)
trap 'rm -rf -- "${workdir}"' EXIT
tar -C "${workdir}" -xzf "${archive}"
(
  cd "${workdir}"
  sha256sum -c checksums.sha256 >/dev/null
)
python3 "${script_dir}/backup_manifest.py" verify --directory "${workdir}" >/dev/null
systemctl is-enabled techflow-state-backup.timer >/dev/null
systemctl is-active techflow-state-backup.timer >/dev/null

echo "backup=valid archive=$(basename -- "${archive}") permissions=valid checksums=valid secrets=excluded timer=active"
