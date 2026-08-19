#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=community-ops-common.sh
source "$SCRIPT_DIR/community-ops-common.sh"

require_root
backup=${1:?사용법: community-restore.sh BACKUP_DIR TARGET_APP TARGET_DB}
target_app=${2:?TARGET_APP가 필요합니다.}
target_db=${3:?TARGET_DB가 필요합니다.}
backup=$(readlink -f "$backup")
require_absolute_safe_path "$backup"
require_absolute_safe_path "$target_app"
[[ "$target_app" != "$APP_ROOT" || ${TECHFLOW_ALLOW_PRODUCTION_RESTORE:-0} == 1 ]] || {
  echo "운영 경로 복원은 TECHFLOW_ALLOW_PRODUCTION_RESTORE=1이 필요합니다." >&2
  exit 2
}
[[ "$target_db" =~ ^[A-Za-z0-9_]+$ ]] || { echo "안전하지 않은 DB 이름입니다." >&2; exit 2; }

"$SCRIPT_DIR/community-verify-backup.sh" "$backup"
work=$(mktemp -d /var/tmp/techflow-community-restore.XXXXXX)
trap 'rm -rf -- "$work"' EXIT INT TERM

start_epoch=$(date +%s)
gpg_decrypt=(gpg --homedir "$GPG_HOME" --batch --yes)
if [[ -n ${TECHFLOW_BACKUP_GPG_PASSPHRASE_FILE:-} ]]; then
  [[ -r "$TECHFLOW_BACKUP_GPG_PASSPHRASE_FILE" ]] || { echo "GPG 암호 파일을 읽을 수 없습니다." >&2; exit 2; }
  gpg_decrypt+=(--pinentry-mode loopback --passphrase-file "$TECHFLOW_BACKUP_GPG_PASSPHRASE_FILE")
fi
for name in database.sql.gz application.tar.gz; do
  "${gpg_decrypt[@]}" --output "$work/$name" \
    --decrypt "$backup/$name.gpg"
done

rm -rf -- "$target_app"
install -d -m 0755 "$target_app"
tar --numeric-owner --xattrs --acls -xzf "$work/application.tar.gz" -C "$target_app"

mariadb -e "DROP DATABASE IF EXISTS \`$target_db\`; CREATE DATABASE \`$target_db\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
gzip -dc "$work/database.sql.gz" | mariadb "$target_db"

APP_ROOT="$target_app" TARGET_DB="$target_db" RESTORE_SOCKET_USER="${TECHFLOW_RESTORE_SOCKET_USER:-}" php <<'PHP'
<?php
$root = getenv('APP_ROOT');
require $root . '/vendor/autoload.php';
$config = require $root . '/config.php';
$config['database']['database'] = getenv('TARGET_DB');
$socketUser = getenv('RESTORE_SOCKET_USER');
if ($socketUser !== '') {
    $config['database']['host'] = 'localhost';
    $config['database']['username'] = $socketUser;
    $config['database']['password'] = '';
}
file_put_contents($root . '/config.php', "<?php\nreturn " . var_export($config, true) . ";\n");
PHP
if [[ -n ${TECHFLOW_RESTORE_SOCKET_USER:-} ]]; then
  [[ "$TECHFLOW_RESTORE_SOCKET_USER" =~ ^[A-Za-z0-9_-]+$ ]] || { echo "안전하지 않은 복구 DB 사용자입니다." >&2; exit 2; }
  mariadb -e "GRANT ALL PRIVILEGES ON \`$target_db\`.* TO '$TECHFLOW_RESTORE_SOCKET_USER'@'localhost'; FLUSH PRIVILEGES;"
fi
chown -R www-data:www-data "$target_app"

db_tables=$(mariadb -NBe "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$target_db'")
app_files=$(find "$target_app" -xdev -type f | wc -l)
duration=$(( $(date +%s) - start_epoch ))
(( db_tables > 0 && app_files > 0 )) || { echo "복원 검증에 실패했습니다." >&2; exit 5; }
printf 'restore=passed target_app=%s target_db=%s tables=%s files=%s rto_seconds=%s\n' \
  "$target_app" "$target_db" "$db_tables" "$app_files" "$duration"
