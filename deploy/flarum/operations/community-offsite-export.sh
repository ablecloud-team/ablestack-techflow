#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=community-ops-common.sh
source "$SCRIPT_DIR/community-ops-common.sh"

require_root
export_user=${1:-ablecloud}
[[ "$export_user" =~ ^[A-Za-z0-9_-]+$ ]] || { echo "안전하지 않은 사용자 이름입니다." >&2; exit 2; }
home=$(getent passwd "$export_user" | cut -d: -f6)
[[ -n "$home" && -d "$home" ]] || { echo "사용자 홈을 찾을 수 없습니다: $export_user" >&2; exit 2; }

latest=$(readlink -f "$BACKUP_ROOT/latest")
"$SCRIPT_DIR/community-verify-backup.sh" "$latest" >/dev/null
export_root="$home/techflow-community-offsite"
install -d -m 0700 -o "$export_user" -g "$export_user" "$export_root"
name=$(basename "$latest")
target="$export_root/$name.tar"
tar -cf "$target.tmp" -C "$(dirname "$latest")" "$name"
chown "$export_user:$export_user" "$target.tmp"
chmod 0600 "$target.tmp"
mv "$target.tmp" "$target"
find "$export_root" -maxdepth 1 -type f -name 'community-*.tar' -mtime +2 -delete
printf 'offsite_export=passed archive=%s bytes=%s\n' "$target" "$(stat -c %s "$target")"
