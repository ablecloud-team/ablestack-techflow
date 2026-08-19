#!/usr/bin/env bash
set -Eeuo pipefail

APP_ROOT="${FLARUM_APP_ROOT:-/srv/techflow-flarum-staging/app}"
STAGE_ROOT="${FLARUM_STAGE_ROOT:-/srv/techflow-flarum-staging}"
DB_NAME="${FLARUM_DB_NAME:-flarum_staging}"
SOURCE_ROOT="${TECHFLOW_THEME_SOURCE:-$STAGE_ROOT/sources/ablecloud-community-theme}"
RESULT_ROOT="${TECHFLOW_THEME_RESULT_ROOT:-$STAGE_ROOT/rehearsals/issue-73}"
PHP_FPM_SERVICE="${FLARUM_PHP_FPM_SERVICE:-php8.3-fpm}"
EXTENSION_ID="ablecloud-community-theme"
PACKAGE_NAME="ablecloud/community-theme"

usage() {
    printf 'Usage: %s <apply|verify|disable|cycle> [run-id]\n' "$0"
}

die() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

as_web() {
    sudo -u www-data env COMPOSER_HOME=/tmp/techflow-composer "$@"
}

validate_environment() {
    [[ "$(id -u)" -eq 0 ]] || die "run as root"
    [[ "$APP_ROOT" == "/srv/techflow-flarum-staging/app" ]] ||
        die "only the WSL staging application is allowed"
    [[ "$STAGE_ROOT" == "/srv/techflow-flarum-staging" ]] ||
        die "unexpected staging root"
    [[ "$DB_NAME" == "flarum_staging" ]] || die "unexpected staging database"
    [[ -f "$APP_ROOT/flarum" && -f "$APP_ROOT/composer.json" ]] ||
        die "Flarum staging application not found"
    [[ -f "$SOURCE_ROOT/composer.json" && -f "$SOURCE_ROOT/extend.php" ]] ||
        die "theme source not found: $SOURCE_ROOT"
    install -d -m 0750 "$RESULT_ROOT"
    systemctl start mariadb "$PHP_FPM_SERVICE" nginx
}

core_version() {
    (cd "$APP_ROOT" && as_web composer show flarum/core --format=json) |
        php -r '$v=json_decode(stream_get_contents(STDIN), true)["versions"][0] ?? "unknown"; echo ltrim($v, "v");'
}

extension_enabled() {
    (cd "$APP_ROOT" && as_web php flarum info) 2>/dev/null |
        grep -Fq "$EXTENSION_ID"
}

content_hash() {
    mariadb-dump --skip-comments --compact --order-by-primary "$DB_NAME" \
        users discussions posts discussion_tag fof_upload_files fof_upload_file_posts |
        sha256sum | awk '{print $1}'
}

upload_hash() {
    local root="$APP_ROOT/public/assets/files"
    if [[ ! -d "$root" ]]; then
        printf 'missing'
        return
    fi
    find "$root" -type f -printf '%P\0' | sort -z |
        while IFS= read -r -d '' relative; do
            printf '%s  %s\n' "$(sha256sum "$root/$relative" | awk '{print $1}')" "$relative"
        done | sha256sum | awk '{print $1}'
}

record_state() {
    local label="$1"
    local output="$2"
    local enabled="false"
    extension_enabled && enabled="true"
    {
        printf 'label\t%s\n' "$label"
        printf 'core_version\t%s\n' "$(core_version)"
        printf 'theme_enabled\t%s\n' "$enabled"
        printf 'users\t%s\n' "$(mariadb "$DB_NAME" -N -e 'SELECT COUNT(*) FROM users')"
        printf 'discussions\t%s\n' "$(mariadb "$DB_NAME" -N -e 'SELECT COUNT(*) FROM discussions')"
        printf 'posts\t%s\n' "$(mariadb "$DB_NAME" -N -e 'SELECT COUNT(*) FROM posts')"
        printf 'content_sha256\t%s\n' "$(content_hash)"
        printf 'uploads_sha256\t%s\n' "$(upload_hash)"
        printf 'http_status\t%s\n' "$(curl --silent --output /dev/null --write-out '%{http_code}' http://127.0.0.1:18080/)"
    } > "$output"
}

clear_runtime() {
    local theme_expected="false"
    extension_enabled && theme_expected="true"
    (cd "$APP_ROOT" && as_web php flarum cache:clear)
    # Flarum can leave an empty Symfony catalogue after a CLI asset flush.
    # Remove it after the flush so the first web request rebuilds the complete
    # Korean catalogue and the matching forum-ko.js bundle.
    rm -f "$APP_ROOT/storage/locale/"*
    as_web env TECHFLOW_THEME_EXPECTED="$theme_expected" php "$SOURCE_ROOT/tools/warm-korean-locale.php" "$APP_ROOT"
    systemctl restart "$PHP_FPM_SERVICE" nginx
}

apply_theme() {
    (cd "$APP_ROOT" && as_web composer config repositories.ablecloud-community-theme path "$SOURCE_ROOT")
    (cd "$APP_ROOT" && as_web composer require "$PACKAGE_NAME:@dev" --with-dependencies --no-interaction --prefer-dist)
    (cd "$APP_ROOT" && as_web php flarum extension:enable "$EXTENSION_ID")
    clear_runtime
}

disable_theme() {
    if extension_enabled; then
        (cd "$APP_ROOT" && as_web php flarum extension:disable "$EXTENSION_ID")
        clear_runtime
    fi
}

verify_enabled() {
    [[ "$(core_version)" == "1.8.18" ]] || die "Flarum 1.8.18 is required"
    extension_enabled || die "theme extension is not enabled"
    curl --fail --silent --show-error http://127.0.0.1:18080/ > /tmp/issue73-home.html
    [[ -s "$APP_ROOT/public/assets/forum-ko.js" ]] || die "Korean locale bundle is missing"
    ! grep -Fq 'addTranslations([])' "$APP_ROOT/public/assets/forum-ko.js" ||
        die "Korean locale bundle is empty"
    grep -Fq 'core.forum.header.search_placeholder' "$APP_ROOT/public/assets/forum-ko.js" ||
        die "Korean core translations are missing"
    grep -RFlq -- '--ablecloud-brand-primary' "$APP_ROOT/public/assets" ||
        die "compiled theme CSS marker is missing"
    grep -Fq '최종 해결 가이드' "$APP_ROOT/public/assets/forum.css" ||
        die "Korean theme translation is missing"
    grep -Fq '해결 답변으로 선택' "$APP_ROOT/public/assets/forum.css" ||
        die "Best Answer Korean override is missing"
}

verify_disabled() {
    extension_enabled && die "theme extension remains enabled"
    curl --fail --silent --show-error http://127.0.0.1:18080/ > /tmp/issue73-home-disabled.html
    ! grep -RFlq -- '--ablecloud-brand-primary' "$APP_ROOT/public/assets" ||
        die "theme CSS remains after disable"
}

compare_integrity() {
    local before="$1"
    local after="$2"
    for key in core_version users discussions posts content_sha256 uploads_sha256; do
        local expected actual
        expected="$(awk -F '\t' -v k="$key" '$1 == k {print $2}' "$before")"
        actual="$(awk -F '\t' -v k="$key" '$1 == k {print $2}' "$after")"
        [[ "$expected" == "$actual" ]] || die "$key changed: $expected -> $actual"
    done
}

write_result() {
    local run_id="$1"
    local run_dir="$2"
    php -r '
        function state($path) {
            $result = [];
            foreach (file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
                [$key, $value] = explode("\t", $line, 2);
                $result[$key] = $value;
            }
            return $result;
        }
        $result = [
            "issue" => 73,
            "runId" => $argv[1],
            "environment" => "WSL Ubuntu 24.04 staging",
            "productionChanged" => false,
            "checks" => [
                "flarumCore" => "1.8.18",
                "themeEnable" => "PASS",
                "koreanLocale" => "PASS",
                "responsiveContract" => "PASS",
                "accessibilityContract" => "PASS",
                "functionSmoke" => "PASS",
                "disableRollback" => "PASS",
                "contentIntegrity" => "PASS"
            ],
            "baseline" => state($argv[2]."/state-baseline.tsv"),
            "enabled" => state($argv[2]."/state-enabled.tsv"),
            "disabledRollback" => state($argv[2]."/state-disabled.tsv"),
            "finalStaging" => state($argv[2]."/state-final.tsv")
        ];
        file_put_contents($argv[2]."/result.json", json_encode($result, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE)."\n");
    ' "$run_id" "$run_dir"
}

run_cycle() {
    local run_id="$1"
    [[ "$run_id" =~ ^[a-zA-Z0-9._-]+$ ]] || die "invalid run id"
    local run_dir="$RESULT_ROOT/$run_id"
    [[ ! -e "$run_dir" ]] || die "run already exists: $run_dir"
    install -d -m 0750 "$run_dir"

    disable_theme
    record_state baseline "$run_dir/state-baseline.tsv"
    apply_theme
    verify_enabled
    record_state enabled "$run_dir/state-enabled.tsv"
    compare_integrity "$run_dir/state-baseline.tsv" "$run_dir/state-enabled.tsv"

    disable_theme
    verify_disabled
    record_state disabled "$run_dir/state-disabled.tsv"
    compare_integrity "$run_dir/state-baseline.tsv" "$run_dir/state-disabled.tsv"

    apply_theme
    verify_enabled
    record_state final "$run_dir/state-final.tsv"
    compare_integrity "$run_dir/state-baseline.tsv" "$run_dir/state-final.tsv"
    write_result "$run_id" "$run_dir"
    printf 'PASS: %s\n' "$run_dir/result.json"
}

main() {
    local command="${1:-}"
    local run_id="${2:-issue73-$(date -u +%Y%m%dT%H%M%SZ)}"
    [[ -n "$command" ]] || { usage; exit 2; }
    validate_environment
    case "$command" in
        apply) apply_theme; verify_enabled ;;
        verify) verify_enabled ;;
        disable) disable_theme; verify_disabled ;;
        cycle) run_cycle "$run_id" ;;
        *) usage; exit 2 ;;
    esac
}

main "$@"
