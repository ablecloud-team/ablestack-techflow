#!/usr/bin/env bash
set -euo pipefail

OPS_CONFIG=${TECHFLOW_COMMUNITY_OPS_CONFIG:-/etc/techflow-community-ops/ops.env}
if [[ -r "$OPS_CONFIG" ]]; then
  # shellcheck disable=SC1090
  source "$OPS_CONFIG"
fi

APP_ROOT=${TECHFLOW_FLARUM_APP_ROOT:-/var/www/html}
BACKUP_ROOT=${TECHFLOW_FLARUM_BACKUP_ROOT:-/var/backups/techflow-flarum/managed}
STATE_ROOT=${TECHFLOW_COMMUNITY_STATE_ROOT:-/var/lib/techflow-community-ops}
LOG_ROOT=${TECHFLOW_COMMUNITY_LOG_ROOT:-/var/log/techflow-community-ops}
GPG_HOME=${TECHFLOW_BACKUP_GPG_HOME:-$STATE_ROOT/gnupg}
BACKUP_RECIPIENT=${TECHFLOW_BACKUP_RECIPIENT:-}
BACKUP_RETENTION_DAYS=${TECHFLOW_BACKUP_RETENTION_DAYS:-30}
BACKUP_MAX_AGE_HOURS=${TECHFLOW_BACKUP_MAX_AGE_HOURS:-30}
FLARUM_LOCAL_URL=${TECHFLOW_FLARUM_LOCAL_URL:-http://127.0.0.1/}
FLARUM_PUBLIC_URL=${TECHFLOW_FLARUM_PUBLIC_URL:-https://community.ablecloud.io}
FLARUM_HOST_HEADER=${TECHFLOW_FLARUM_HOST_HEADER:-community.ablecloud.io}
AI_HEALTH_URL=${TECHFLOW_AI_HEALTH_URL:-https://techflow.ablecloud.io/api/v1/health}
DISK_WARN_PERCENT=${TECHFLOW_DISK_WARN_PERCENT:-70}
DISK_CRITICAL_PERCENT=${TECHFLOW_DISK_CRITICAL_PERCENT:-85}
ALERT_COOLDOWN_SECONDS=${TECHFLOW_ALERT_COOLDOWN_SECONDS:-3600}
PHP_FPM_SERVICE=${TECHFLOW_PHP_FPM_SERVICE:-php8.3-fpm}
ALLOWED_MAIL_DRIVERS=${TECHFLOW_ALLOWED_MAIL_DRIVERS:-smtp}

require_root() {
  if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
    echo "root 권한이 필요합니다." >&2
    exit 2
  fi
}

require_absolute_safe_path() {
  local value=$1
  case "$value" in
    /*) ;;
    *) echo "절대 경로가 필요합니다: $value" >&2; exit 2 ;;
  esac
  [[ "$value" != "/" && "$value" != "/var" && "$value" != "/srv" ]] || {
    echo "너무 넓은 경로는 사용할 수 없습니다: $value" >&2
    exit 2
  }
}

prepare_runtime_dirs() {
  require_absolute_safe_path "$BACKUP_ROOT"
  require_absolute_safe_path "$STATE_ROOT"
  require_absolute_safe_path "$LOG_ROOT"
  install -d -m 0700 -o root -g root "$BACKUP_ROOT" "$STATE_ROOT" "$GPG_HOME"
  install -d -m 0750 -o root -g adm "$LOG_ROOT"
}

load_database_config() {
  [[ -r "$APP_ROOT/config.php" && -r "$APP_ROOT/vendor/autoload.php" ]] || {
    echo "Flarum config 또는 vendor/autoload.php를 읽을 수 없습니다: $APP_ROOT" >&2
    exit 2
  }
  local exported
  exported=$(APP_ROOT="$APP_ROOT" php <<'PHP'
<?php
$root = getenv('APP_ROOT');
require $root . '/vendor/autoload.php';
$config = require $root . '/config.php';
$db = $config['database'];
foreach (['host', 'port', 'database', 'username', 'password', 'prefix'] as $key) {
    printf("DB_%s=%s\n", strtoupper($key), escapeshellarg((string) ($db[$key] ?? '')));
}
PHP
  )
  eval "$exported"
  : "${DB_DATABASE:?database name is required}"
  : "${DB_USERNAME:?database username is required}"
}

make_client_config() {
  local target=$1
  umask 077
  {
    printf '[client]\n'
    if [[ ${TECHFLOW_DB_USE_ROOT_SOCKET:-0} == 1 ]]; then
      printf 'user=root\nprotocol=socket\n'
    else
      printf 'host=%s\n' "$DB_HOST"
      [[ -z "$DB_PORT" ]] || printf 'port=%s\n' "$DB_PORT"
      printf 'user=%s\n' "$DB_USERNAME"
      printf 'password=%s\n' "$DB_PASSWORD"
    fi
    printf 'default-character-set=utf8mb4\n'
  } >"$target"
  chmod 0600 "$target"
}

sha256_file() {
  sha256sum "$1" | awk '{print $1}'
}
