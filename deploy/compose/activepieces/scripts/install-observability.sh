#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
deploy_dir=$(cd -- "${script_dir}/.." && pwd)
systemd_dir="${deploy_dir}/systemd"

if [[ ${EUID} -ne 0 ]]; then
  echo "Run this command with sudo." >&2
  exit 1
fi

install -d -m 0750 -o root -g ablecloud /var/lib/ablestack-techflow/observability
install -d -m 0750 -o root -g ablecloud /var/log/ablestack-techflow/observability
install -d -m 0755 -o root -g root /usr/local/libexec
install -m 0755 "${deploy_dir}/observability/observer.py" /usr/local/libexec/techflow-observer
install -m 0644 "${systemd_dir}/techflow-observer.service" /etc/systemd/system/techflow-observer.service
install -m 0644 "${systemd_dir}/techflow-observer.timer" /etc/systemd/system/techflow-observer.timer
install -m 0644 "${systemd_dir}/techflow-observer-notify@.service" /etc/systemd/system/techflow-observer-notify@.service

systemctl daemon-reload
systemctl enable --now techflow-observer.timer
systemctl start techflow-observer.service
systemctl is-enabled techflow-observer.timer
systemctl is-active techflow-observer.timer
systemctl status techflow-observer.service --no-pager || true
