#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
    echo "run as root" >&2
    exit 1
fi

source_root="${1:-}"
change_id="${2:-}"
app_root="/var/www/html"
extension_root="$app_root/extensions/ablecloud-community-theme"
backup_root="/var/backups/techflow-flarum/$change_id"

if [[ -z "$source_root" || -z "$change_id" ]]; then
    echo "usage: $0 /tmp/ablecloud-community-theme-<id> theme-<id>" >&2
    exit 1
fi

source_root="$(realpath "$source_root")"
extension_root="$(realpath "$extension_root")"

[[ "$source_root" == /tmp/ablecloud-community-theme-* ]] || {
    echo "unexpected source path: $source_root" >&2
    exit 1
}
[[ "$extension_root" == "/var/www/html/extensions/ablecloud-community-theme" ]] || {
    echo "unexpected extension path: $extension_root" >&2
    exit 1
}
[[ "$backup_root" == /var/backups/techflow-flarum/theme-* ]] || {
    echo "unexpected backup path: $backup_root" >&2
    exit 1
}
[[ -f "$source_root/resources/less/forum.less" ]] || {
    echo "theme source is incomplete" >&2
    exit 1
}

install -d -m 0750 "$backup_root"
cp -a "$extension_root" "$backup_root/extension-before"
cp -a "$app_root/vendor/ablecloud/community-theme" "$backup_root/vendor-before"
cp -a "$app_root/composer.json" "$app_root/composer.lock" "$backup_root/"
cp -a "$app_root/public/assets" "$backup_root/assets-before"
if [[ -d "$app_root/storage/locale" ]]; then
    cp -a "$app_root/storage/locale" "$backup_root/locale-before"
fi

rsync -a --delete "$source_root/" "$extension_root/"
cd "$app_root"
sudo -u www-data env COMPOSER_HOME=/tmp/techflow-composer \
    composer require ablecloud/community-theme:@dev --with-dependencies --no-interaction
sudo -u www-data php flarum extension:enable ablecloud-community-theme
sudo -u www-data php flarum cache:clear
sudo -u www-data env TECHFLOW_ALLOWED_FLARUM_ROOT="$app_root" \
    php vendor/ablecloud/community-theme/tools/warm-korean-locale.php "$app_root"
systemctl restart php8.3-fpm nginx

systemctl is-active --quiet nginx
systemctl is-active --quiet php8.3-fpm
systemctl is-active --quiet mariadb
curl --fail --silent --show-error --output /dev/null \
    -H 'Host: community.ablecloud.io' \
    -H 'X-Forwarded-Proto: https' \
    http://127.0.0.1/
grep -q 'UserPage-nav > ul.affix' \
    "$app_root/vendor/ablecloud/community-theme/resources/less/forum.less"
grep -q 'ul.affix' "$app_root/public/assets/forum.css"

printf 'BACKUP_ROOT=%s\n' "$backup_root"
printf 'SOURCE_SHA256='
sha256sum "$source_root/resources/less/forum.less" | awk '{print $1}'
printf 'VENDOR_SHA256='
sha256sum "$app_root/vendor/ablecloud/community-theme/resources/less/forum.less" | awk '{print $1}'
printf 'LOCAL_HTTP=200\n'
printf 'RESULT=PASS\n'
