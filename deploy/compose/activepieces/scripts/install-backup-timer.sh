#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
deploy_dir=$(cd -- "${script_dir}/.." && pwd)
systemd_dir="${deploy_dir}/systemd"

if [[ ${EUID} -ne 0 ]]; then
  echo "Run this command with sudo." >&2
  exit 1
fi

install -d -m 0750 -o root -g ablecloud /var/backups/ablestack-techflow/state
install -d -m 0750 -o root -g ablecloud /var/log/ablestack-techflow/recovery-drills
install -m 0644 "${systemd_dir}/techflow-state-backup.service" \
  /etc/systemd/system/techflow-state-backup.service
install -m 0644 "${systemd_dir}/techflow-state-backup.timer" \
  /etc/systemd/system/techflow-state-backup.timer
systemctl daemon-reload
systemctl enable --now techflow-state-backup.timer
systemctl is-enabled techflow-state-backup.timer
systemctl is-active techflow-state-backup.timer
systemctl list-timers techflow-state-backup.timer --no-pager
