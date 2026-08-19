#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=community-ops-common.sh
source "$SCRIPT_DIR/community-ops-common.sh"

require_root
prepare_runtime_dirs
exec 9>"$STATE_ROOT/monitor.lock"
flock -n 9 || exit 0
exec 8>"$STATE_ROOT/backup.lock"
if ! flock -n 8; then
  echo "monitor=skipped reason=backup-in-progress"
  exit 0
fi

now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
tmp=$(mktemp "$STATE_ROOT/status.XXXXXX")
alerts_tmp=$(mktemp "$STATE_ROOT/alerts.XXXXXX")
trap 'rm -f "$tmp" "$alerts_tmp"' EXIT INT TERM

declare -a alerts=()
declare -A service_state=()
for service in nginx "$PHP_FPM_SERVICE" mariadb; do
  state=$(systemctl is-active "$service" 2>/dev/null || true)
  service_state["$service"]=$state
  [[ "$state" == active ]] || alerts+=("CRITICAL:service:$service:$state")
done

probe() {
  local url=$1 host_header=${2:-}
  local output
  if [[ -n "$host_header" ]]; then
    output=$(curl -kfsS --max-time 15 -H "Host: $host_header" -H 'X-Forwarded-Proto: https' \
      -o /dev/null -w '%{http_code} %{time_total}' "$url" 2>/dev/null) || output="000 15"
  else
    output=$(curl -kfsS --max-time 15 -o /dev/null -w '%{http_code} %{time_total}' "$url" 2>/dev/null) || output="000 15"
  fi
  printf '%s' "$output"
}

read -r local_code local_time <<<"$(probe "$FLARUM_LOCAL_URL" "$FLARUM_HOST_HEADER")"
read -r public_code public_time <<<"$(probe "$FLARUM_PUBLIC_URL")"
read -r ai_code ai_time <<<"$(probe "$AI_HEALTH_URL")"
[[ "$local_code" == 200 ]] || alerts+=("CRITICAL:http:community-local:$local_code")
[[ "$public_code" == 200 ]] || alerts+=("CRITICAL:http:community-public:$public_code")
[[ "$ai_code" == 200 ]] || alerts+=("WARNING:http:ai-orchestration:$ai_code")

disk_used=$(df -P "$APP_ROOT" | awk 'NR==2 {gsub(/%/,"",$5); print $5}')
inode_used=$(df -Pi "$APP_ROOT" | awk 'NR==2 {gsub(/%/,"",$5); print $5}')
if (( disk_used >= DISK_CRITICAL_PERCENT || inode_used >= DISK_CRITICAL_PERCENT )); then
  alerts+=("CRITICAL:capacity:filesystem:${disk_used}/${inode_used}")
elif (( disk_used >= DISK_WARN_PERCENT || inode_used >= DISK_WARN_PERCENT )); then
  alerts+=("WARNING:capacity:filesystem:${disk_used}/${inode_used}")
fi

latest_manifest=$(readlink -f "$BACKUP_ROOT/latest/manifest.json" 2>/dev/null || true)
backup_age=-1
backup_ok=0
if [[ -r "$latest_manifest" ]]; then
  backup_age=$(( $(date +%s) - $(stat -c %Y "$latest_manifest") ))
  if "$SCRIPT_DIR/community-verify-backup.sh" "$(dirname "$latest_manifest")" >/dev/null 2>&1; then
    backup_ok=1
  fi
fi
if (( backup_ok == 0 )); then
  alerts+=("CRITICAL:backup:integrity:failed")
fi

upload_bytes=$(du -sb "$APP_ROOT/public/assets" 2>/dev/null | awk '{print $1}' || printf 0)
log_errors=$(journalctl -u nginx -u "$PHP_FPM_SERVICE" -u mariadb --since '-5 minutes' --no-pager 2>/dev/null \
  | grep -Eic 'fatal|panic|critical|segfault|out of memory' || true)
(( log_errors == 0 )) || alerts+=("WARNING:logs:critical-lines:$log_errors")

db_client=$(mktemp "$STATE_ROOT/db-client.XXXXXX")
trap 'rm -f "$tmp" "$alerts_tmp" "$db_client"' EXIT INT TERM
load_database_config
make_client_config "$db_client"
settings_table="${DB_PREFIX}settings"
[[ "$settings_table" =~ ^[A-Za-z0-9_]+$ ]] || { echo "안전하지 않은 settings 테이블 이름입니다." >&2; exit 2; }
mail_driver=$(mariadb --defaults-extra-file="$db_client" -NBe \
  "SELECT value FROM \`$settings_table\` WHERE \`key\`='mail_driver' LIMIT 1" "$DB_DATABASE" 2>/dev/null || true)
rm -f "$db_client"
unset DB_PASSWORD
mail_driver_allowed=0
IFS=',' read -r -a allowed_mail_drivers <<<"$ALLOWED_MAIL_DRIVERS"
for allowed in "${allowed_mail_drivers[@]}"; do
  [[ "$mail_driver" != "$allowed" ]] || mail_driver_allowed=1
done
(( mail_driver_allowed == 1 )) || alerts+=("CRITICAL:security:mail-driver:${mail_driver:-unset}")

printf '%s\n' "${alerts[@]:-}" | sed '/^$/d' >"$alerts_tmp"
STATUS_PATH="$tmp" ALERTS_PATH="$alerts_tmp" NOW="$now" \
  LOCAL_CODE="$local_code" LOCAL_TIME="$local_time" PUBLIC_CODE="$public_code" PUBLIC_TIME="$public_time" \
  AI_CODE="$ai_code" AI_TIME="$ai_time" DISK_USED="$disk_used" INODE_USED="$inode_used" \
  BACKUP_AGE="$backup_age" BACKUP_OK="$backup_ok" UPLOAD_BYTES="$upload_bytes" LOG_ERRORS="$log_errors" MAIL_DRIVER="$mail_driver" \
  NGINX_STATE="${service_state[nginx]}" PHP_STATE="${service_state[$PHP_FPM_SERVICE]}" MARIA_STATE="${service_state[mariadb]}" \
  python3 <<'PY'
import json
import os
from pathlib import Path

alerts = [line for line in Path(os.environ['ALERTS_PATH']).read_text().splitlines() if line]
status = {
    'schemaVersion': 1,
    'collectedAt': os.environ['NOW'],
    'services': {'nginx': os.environ['NGINX_STATE'], 'php-fpm': os.environ['PHP_STATE'], 'mariadb': os.environ['MARIA_STATE']},
    'http': {
        'communityLocal': {'code': int(os.environ['LOCAL_CODE']), 'seconds': float(os.environ['LOCAL_TIME'])},
        'communityPublic': {'code': int(os.environ['PUBLIC_CODE']), 'seconds': float(os.environ['PUBLIC_TIME'])},
        'aiOrchestration': {'code': int(os.environ['AI_CODE']), 'seconds': float(os.environ['AI_TIME'])},
    },
    'capacity': {'diskUsedPercent': int(os.environ['DISK_USED']), 'inodeUsedPercent': int(os.environ['INODE_USED']), 'uploadBytes': int(os.environ['UPLOAD_BYTES'])},
    'backup': {'ageSeconds': int(os.environ['BACKUP_AGE']), 'integrity': os.environ['BACKUP_OK'] == '1'},
    'security': {'mailDriver': os.environ['MAIL_DRIVER'] or 'unset'},
    'criticalLogLines5m': int(os.environ['LOG_ERRORS']),
    'alerts': alerts,
}
Path(os.environ['STATUS_PATH']).write_text(json.dumps(status, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
PY
install -m 0640 -o root -g adm "$tmp" "$STATE_ROOT/status.json"

cat >"$STATE_ROOT/metrics.prom.tmp" <<EOF
techflow_community_service_up{service="nginx"} $([[ ${service_state[nginx]} == active ]] && echo 1 || echo 0)
techflow_community_service_up{service="php-fpm"} $([[ ${service_state[$PHP_FPM_SERVICE]} == active ]] && echo 1 || echo 0)
techflow_community_service_up{service="mariadb"} $([[ ${service_state[mariadb]} == active ]] && echo 1 || echo 0)
techflow_community_http_status{endpoint="local"} $local_code
techflow_community_http_status{endpoint="public"} $public_code
techflow_community_http_status{endpoint="ai-orchestration"} $ai_code
techflow_community_http_duration_seconds{endpoint="local"} $local_time
techflow_community_http_duration_seconds{endpoint="public"} $public_time
techflow_community_http_duration_seconds{endpoint="ai-orchestration"} $ai_time
techflow_community_disk_used_percent $disk_used
techflow_community_inode_used_percent $inode_used
techflow_community_upload_bytes $upload_bytes
techflow_community_backup_age_seconds $backup_age
techflow_community_backup_integrity $backup_ok
techflow_community_critical_log_lines_5m $log_errors
techflow_community_mail_driver_allowed $mail_driver_allowed
techflow_community_active_alerts ${#alerts[@]}
EOF
chmod 0640 "$STATE_ROOT/metrics.prom.tmp"
chown root:adm "$STATE_ROOT/metrics.prom.tmp"
mv "$STATE_ROOT/metrics.prom.tmp" "$STATE_ROOT/metrics.prom"

fingerprint=$(sha256sum "$alerts_tmp" | awk '{print $1}')
last_fingerprint=$(cat "$STATE_ROOT/last-alert.fingerprint" 2>/dev/null || true)
last_sent=$(cat "$STATE_ROOT/last-alert.epoch" 2>/dev/null || echo 0)
current_epoch=$(date +%s)

if [[ "$fingerprint" != "$last_fingerprint" || $((current_epoch - last_sent)) -ge $ALERT_COOLDOWN_SECONDS ]]; then
  if [[ -r /etc/techflow-community-ops/alert.env ]]; then
    # shellcheck disable=SC1091
    source /etc/techflow-community-ops/alert.env
  fi
  if [[ -n ${TECHFLOW_CHAT_WEBHOOK_URL:-} ]]; then
    if ((${#alerts[@]} == 0)); then
      text="[Community 운영] 모든 점검 항목이 정상으로 복구되었습니다."
    else
      text="[Community 운영 경보] ${#alerts[@]}건 - $(IFS=', '; echo "${alerts[*]}")"
    fi
    payload=$(TEXT="$text" URL="$FLARUM_PUBLIC_URL" python3 -c 'import json,os; print(json.dumps({"text":os.environ["TEXT"],"url":os.environ["URL"]}, ensure_ascii=False))')
    curl -fsS --max-time 15 -X POST --data-urlencode "payload=$payload" "$TECHFLOW_CHAT_WEBHOOK_URL" >/dev/null || true
  fi
  printf '%s' "$fingerprint" >"$STATE_ROOT/last-alert.fingerprint"
  printf '%s' "$current_epoch" >"$STATE_ROOT/last-alert.epoch"
fi

printf '%s\t%s\talerts=%s\n' "$now" "$fingerprint" "${#alerts[@]}" >>"$LOG_ROOT/monitor.log"
if ((${#alerts[@]} > 0)); then
  printf 'monitor=alert count=%s status=%s\n' "${#alerts[@]}" "$STATE_ROOT/status.json"
  exit 2
fi
printf 'monitor=passed services=3/3 http=200/200/200 backup=passed disk=%s%% inode=%s%%\n' "$disk_used" "$inode_used"
