#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
action=${1:-install}
site_path=${TECHFLOW_NGINX_SITE_PATH:-/etc/nginx/sites-available/flarum}

[[ ${EUID:-$(id -u)} -eq 0 ]] || { echo "root 권한이 필요합니다." >&2; exit 2; }

install_assets() {
  install -d -m 0750 /usr/local/libexec/techflow-community-ops
  for name in community-ops-common.sh community-backup.sh community-verify-backup.sh community-restore.sh community-monitor.sh community-offsite-export.sh alert_policy.py; do
    install -m 0750 "$SCRIPT_DIR/$name" "/usr/local/libexec/techflow-community-ops/$name"
  done
  install -d -m 0700 /etc/techflow-community-ops /var/lib/techflow-community-ops/gnupg /var/backups/techflow-flarum/managed
  install -d -m 0750 -o root -g adm /var/log/techflow-community-ops
  if [[ ! -e /etc/techflow-community-ops/ops.env ]]; then
    install -m 0600 "$SCRIPT_DIR/ops.env.example" /etc/techflow-community-ops/ops.env
  fi
  install -m 0644 "$SCRIPT_DIR/techflow-community-backup.service" /etc/systemd/system/
  install -m 0644 "$SCRIPT_DIR/techflow-community-backup.timer" /etc/systemd/system/
  install -m 0644 "$SCRIPT_DIR/techflow-community-monitor.service" /etc/systemd/system/
  install -m 0644 "$SCRIPT_DIR/techflow-community-monitor.timer" /etc/systemd/system/
  install -m 0644 "$SCRIPT_DIR/techflow-community-ops.logrotate" /etc/logrotate.d/techflow-community-ops
  systemctl daemon-reload
  systemctl enable --now techflow-community-backup.timer techflow-community-monitor.timer
}

apply_security() {
  [[ -f "$site_path" ]] || { echo "Nginx 사이트 파일을 찾을 수 없습니다: $site_path" >&2; exit 2; }
  stamp=$(date -u +%Y%m%dT%H%M%SZ)
  backup_dir="/var/backups/techflow-flarum/security-$stamp"
  had_zone=0
  had_server=0
  install -d -m 0700 "$backup_dir"
  cp -a "$site_path" "$backup_dir/flarum-site.conf"
  if [[ -e /etc/nginx/conf.d/techflow-community-security-zone.conf ]]; then
    cp -a /etc/nginx/conf.d/techflow-community-security-zone.conf "$backup_dir/"
    had_zone=1
  fi
  if [[ -e /etc/nginx/snippets/techflow-community-security-server.conf ]]; then
    cp -a /etc/nginx/snippets/techflow-community-security-server.conf "$backup_dir/"
    had_server=1
  fi
  install -m 0644 "$SCRIPT_DIR/nginx-community-security-zone.conf" /etc/nginx/conf.d/techflow-community-security-zone.conf
  install -m 0644 "$SCRIPT_DIR/nginx-community-security-server.conf" /etc/nginx/snippets/techflow-community-security-server.conf
  if ! grep -qF 'include /etc/nginx/snippets/techflow-community-security-server.conf;' "$site_path"; then
    SITE_PATH="$site_path" python3 <<'PY'
import os
from pathlib import Path

path = Path(os.environ['SITE_PATH'])
text = path.read_text(encoding='utf-8')
marker = 'server {'
if marker not in text:
    raise SystemExit('server 블록을 찾을 수 없습니다.')
text = text.replace(marker, marker + '\n    include /etc/nginx/snippets/techflow-community-security-server.conf;', 1)
path.write_text(text, encoding='utf-8')
PY
  fi
  if ! nginx -t || ! systemctl reload nginx; then
    cp -a "$backup_dir/flarum-site.conf" "$site_path"
    if [[ $had_zone -eq 1 ]]; then
      cp -a "$backup_dir/techflow-community-security-zone.conf" /etc/nginx/conf.d/techflow-community-security-zone.conf
    else
      rm -f /etc/nginx/conf.d/techflow-community-security-zone.conf
    fi
    if [[ $had_server -eq 1 ]]; then
      cp -a "$backup_dir/techflow-community-security-server.conf" /etc/nginx/snippets/techflow-community-security-server.conf
    else
      rm -f /etc/nginx/snippets/techflow-community-security-server.conf
    fi
    nginx -t && systemctl reload nginx || true
    echo "Nginx 검증 실패로 원복했습니다: $backup_dir" >&2
    exit 4
  fi
  printf 'security=applied backup=%s\n' "$backup_dir"
}

case "$action" in
  install) install_assets ;;
  apply-security) apply_security ;;
  install-all) install_assets; apply_security ;;
  *) echo "사용법: $0 {install|apply-security|install-all}" >&2; exit 2 ;;
esac
