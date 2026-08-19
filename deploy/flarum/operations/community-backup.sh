#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=community-ops-common.sh
source "$SCRIPT_DIR/community-ops-common.sh"

require_root
prepare_runtime_dirs
require_absolute_safe_path "$APP_ROOT"
[[ -d "$APP_ROOT" ]] || { echo "Flarum 경로가 없습니다: $APP_ROOT" >&2; exit 2; }
[[ -n "$BACKUP_RECIPIENT" ]] || { echo "TECHFLOW_BACKUP_RECIPIENT가 필요합니다." >&2; exit 2; }
command -v gpg >/dev/null
command -v mariadb-dump >/dev/null

exec 9>"$STATE_ROOT/backup.lock"
flock -w 120 9 || { echo "운영 점검 또는 다른 백업이 진행 중입니다." >&2; exit 3; }

timestamp=$(date -u +%Y%m%dT%H%M%SZ)
backup_name="community-$timestamp"
partial="$BACKUP_ROOT/.partial-$backup_name"
final="$BACKUP_ROOT/$backup_name"
client_config="$partial/.mariadb.cnf"
php_was_active=0

cleanup() {
  local status=$?
  if [[ $php_was_active -eq 1 ]] && ! systemctl is-active --quiet "$PHP_FPM_SERVICE"; then
    systemctl start "$PHP_FPM_SERVICE" || true
  fi
  rm -f "$client_config"
  if [[ $status -ne 0 ]]; then
    rm -rf -- "$partial"
  fi
  exit "$status"
}
trap cleanup EXIT INT TERM

install -d -m 0700 "$partial"
load_database_config
make_client_config "$client_config"

if systemctl is-active --quiet "$PHP_FPM_SERVICE"; then
  php_was_active=1
  systemctl stop "$PHP_FPM_SERVICE"
fi

mariadb-dump --defaults-extra-file="$client_config" \
  --single-transaction --quick --routines --events --triggers --hex-blob \
  --default-character-set=utf8mb4 "$DB_DATABASE" | gzip -9 >"$partial/database.sql.gz"

tar --numeric-owner --xattrs --acls -czf "$partial/application.tar.gz" \
  --exclude='./storage/cache/*' --exclude='./storage/logs/*' \
  -C "$APP_ROOT" .

if [[ $php_was_active -eq 1 ]]; then
  systemctl start "$PHP_FPM_SERVICE"
  php_was_active=0
fi
rm -f "$client_config"
unset DB_PASSWORD

for plain in database.sql.gz application.tar.gz; do
  gpg --homedir "$GPG_HOME" --batch --yes --trust-model always \
    --recipient "$BACKUP_RECIPIENT" --output "$partial/$plain.gpg" \
    --encrypt "$partial/$plain"
  rm -f "$partial/$plain"
done

BACKUP_DIR="$partial" BACKUP_NAME="$backup_name" DB_NAME="$DB_DATABASE" python3 <<'PY'
import hashlib
import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path

root = Path(os.environ['BACKUP_DIR'])
files = {}
for path in sorted(root.glob('*.gpg')):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    files[path.name] = {'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}
manifest = {
    'schemaVersion': 1,
    'backup': os.environ['BACKUP_NAME'],
    'createdAt': datetime.now(timezone.utc).isoformat(),
    'host': platform.node(),
    'database': os.environ['DB_NAME'],
    'consistency': 'php-fpm-quiesced',
    'encryption': 'OpenPGP public-key',
    'files': files,
}
(root / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
PY

chmod 0600 "$partial"/*
mv "$partial" "$final"
if ! "$SCRIPT_DIR/community-verify-backup.sh" "$final"; then
  rm -rf -- "$final"
  echo "검증에 실패한 백업을 제거했습니다." >&2
  exit 5
fi
ln -sfn "$backup_name" "$BACKUP_ROOT/latest"
find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -name 'community-*' \
  -mtime "+$BACKUP_RETENTION_DAYS" -print -exec rm -rf -- {} +

printf 'backup=passed archive=%s encryption=openpgp consistency=php-fpm-quiesced\n' "$final"
