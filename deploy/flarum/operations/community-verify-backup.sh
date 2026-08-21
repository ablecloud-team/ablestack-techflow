#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=community-ops-common.sh
source "$SCRIPT_DIR/community-ops-common.sh"

target=${1:-$BACKUP_ROOT/latest}
target=$(readlink -f "$target")
require_absolute_safe_path "$target"
[[ -d "$target" && -r "$target/manifest.json" ]] || { echo "백업 Manifest가 없습니다: $target" >&2; exit 2; }

BACKUP_DIR="$target" python3 <<'PY'
import hashlib
import json
import os
from pathlib import Path

root = Path(os.environ['BACKUP_DIR'])
manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
if manifest.get('schemaVersion') != 1 or manifest.get('encryption') != 'OpenPGP public-key':
    raise SystemExit('지원하지 않는 백업 Manifest입니다.')
for name, expected in manifest['files'].items():
    path = root / name
    if not path.is_file():
        raise SystemExit(f'백업 파일이 없습니다: {name}')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    if path.stat().st_size != expected['bytes'] or digest.hexdigest() != expected['sha256']:
        raise SystemExit(f'백업 무결성 오류: {name}')
print(f"manifest=passed files={len(manifest['files'])}")
PY

for encrypted in "$target"/*.gpg; do
  gpg --homedir "$GPG_HOME" --batch --list-only --list-packets "$encrypted" >/dev/null
done

age_seconds=$(( $(date +%s) - $(stat -c %Y "$target/manifest.json") ))
if (( age_seconds > BACKUP_MAX_AGE_HOURS * 3600 )); then
  echo "백업이 허용 시간을 초과했습니다: ${age_seconds}s" >&2
  exit 4
fi
printf 'backup_verify=passed age_seconds=%s path=%s\n' "$age_seconds" "$target"
