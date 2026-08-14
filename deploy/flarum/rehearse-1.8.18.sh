#!/usr/bin/env bash
set -Eeuo pipefail

APP_ROOT="${FLARUM_APP_ROOT:-/srv/techflow-flarum-staging/app}"
STAGE_ROOT="${FLARUM_STAGE_ROOT:-/srv/techflow-flarum-staging}"
DB_NAME="${FLARUM_DB_NAME:-flarum_staging}"
TARGET_VERSION="${FLARUM_TARGET_VERSION:-1.8.18}"
NICKNAMES_VERSION="${FLARUM_NICKNAMES_VERSION:-1.8.3}"
MAILER_VERSION="${FLARUM_MAILER_VERSION:-6.1.11}"
RESULT_ROOT="${FLARUM_RESULT_ROOT:-$STAGE_ROOT/rehearsals/issue-71}"
PHP_FPM_SERVICE="${FLARUM_PHP_FPM_SERVICE:-php8.3-fpm}"

usage() {
    cat <<'EOF'
Usage: rehearse-1.8.18.sh <snapshot|preflight|upgrade|verify|rollback|cycle> <cycle-id>

Commands:
  snapshot   Save the application, database, and integrity baseline.
  preflight  Check Composer compatibility with Flarum 1.8.18.
  upgrade    Upgrade the saved cycle to Flarum 1.8.18.
  verify     Record and validate the current runtime state.
  rollback   Restore the saved application and database baseline.
  cycle      Run snapshot, preflight, upgrade, verify, and rollback.
EOF
}

die() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

require_command() {
    command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

validate_environment() {
    [[ "$(id -u)" -eq 0 ]] || die "run as root"
    [[ "$APP_ROOT" == "/srv/techflow-flarum-staging/app" ]] ||
        die "unexpected staging application path: $APP_ROOT"
    [[ "$STAGE_ROOT" == "/srv/techflow-flarum-staging" ]] ||
        die "unexpected staging root: $STAGE_ROOT"
    [[ "$DB_NAME" == "flarum_staging" ]] || die "unexpected database: $DB_NAME"
    [[ -f "$APP_ROOT/flarum" && -f "$APP_ROOT/composer.json" ]] ||
        die "Flarum application not found at $APP_ROOT"
    require_command composer
    require_command curl
    require_command gzip
    require_command mariadb
    require_command mariadb-dump
    require_command rsync
    require_command sha256sum
    require_command sudo
    install -d -m 0750 "$RESULT_ROOT"
    systemctl start mariadb "$PHP_FPM_SERVICE" nginx
}

restore_services() {
    systemctl start mariadb "$PHP_FPM_SERVICE" nginx >/dev/null 2>&1 || true
}

cycle_dir() {
    local cycle_id="$1"
    [[ "$cycle_id" =~ ^[a-zA-Z0-9._-]+$ ]] || die "invalid cycle id: $cycle_id"
    printf '%s/%s' "$RESULT_ROOT" "$cycle_id"
}

as_web() {
    sudo -u www-data env COMPOSER_HOME=/tmp/techflow-composer "$@"
}

core_version() {
    (cd "$APP_ROOT" && as_web composer show flarum/core --format=json) |
        php -r '$v=json_decode(stream_get_contents(STDIN), true)["versions"][0] ?? "unknown"; echo ltrim($v, "v");'
}

package_version() {
    local package_name="$1"
    (cd "$APP_ROOT" && as_web composer show "$package_name" --format=json) |
        php -r '$v=json_decode(stream_get_contents(STDIN), true)["versions"][0] ?? "unknown"; echo ltrim($v, "v");'
}

db_hash() {
    mariadb-dump --skip-comments --compact --order-by-primary "$DB_NAME" | sha256sum | awk '{print $1}'
}

business_db_hash() {
    mariadb-dump --skip-comments --compact --order-by-primary \
        --ignore-table="$DB_NAME.access_tokens" "$DB_NAME" |
        sha256sum |
        awk '{print $1}'
}

upload_hash() {
    local upload_root="$APP_ROOT/public/assets/files"
    if [[ ! -d "$upload_root" ]]; then
        printf 'missing'
        return
    fi
    find "$upload_root" -type f -printf '%P\0' |
        sort -z |
        while IFS= read -r -d '' relative; do
            printf '%s  %s\n' "$(sha256sum "$upload_root/$relative" | awk '{print $1}')" "$relative"
        done |
        sha256sum |
        awk '{print $1}'
}

record_state() {
    local label="$1"
    local output_dir="$2"
    local state_file="$output_dir/state-$label.tsv"
    local info_file="$output_dir/flarum-info-$label.txt"
    local direct_file="$output_dir/composer-direct-$label.json"
    local users discussions posts uploads upload_bytes

    users="$(mariadb "$DB_NAME" -N -e 'SELECT COUNT(*) FROM users')"
    discussions="$(mariadb "$DB_NAME" -N -e 'SELECT COUNT(*) FROM discussions')"
    posts="$(mariadb "$DB_NAME" -N -e 'SELECT COUNT(*) FROM posts')"
    uploads="$(find "$APP_ROOT/public/assets/files" -type f 2>/dev/null | wc -l)"
    upload_bytes="$(du -sb "$APP_ROOT/public/assets/files" 2>/dev/null | awk '{print $1}')"

    {
        printf 'core_version\t%s\n' "$(core_version)"
        printf 'nicknames_version\t%s\n' "$(package_version flarum/nicknames)"
        printf 'mailer_version\t%s\n' "$(package_version symfony/mailer)"
        printf 'users\t%s\n' "$users"
        printf 'discussions\t%s\n' "$discussions"
        printf 'posts\t%s\n' "$posts"
        printf 'upload_files\t%s\n' "$uploads"
        printf 'upload_bytes\t%s\n' "${upload_bytes:-0}"
        printf 'upload_sha256\t%s\n' "$(upload_hash)"
        printf 'database_sha256\t%s\n' "$(db_hash)"
        printf 'business_database_sha256\t%s\n' "$(business_db_hash)"
    } > "$state_file"

    (cd "$APP_ROOT" && as_web php flarum info) > "$info_file" 2>&1
    (cd "$APP_ROOT" && as_web composer show --direct --format=json) > "$direct_file"
    chmod 0640 "$state_file" "$info_file" "$direct_file"
}

rebuild_runtime() {
    install -d -o www-data -g www-data \
        "$APP_ROOT/storage/cache" \
        "$APP_ROOT/storage/locale" \
        "$APP_ROOT/storage/logs" \
        "$APP_ROOT/storage/views"
    chown -R www-data:www-data "$APP_ROOT"
    chmod -R u+rwX,g+rwX "$APP_ROOT/storage" "$APP_ROOT/public/assets"
    rm -f "$APP_ROOT/storage/locale/"*
    rm -f "$APP_ROOT/public/assets/forum-ko.js" "$APP_ROOT/public/assets/forum-ko.js.map"
    (cd "$APP_ROOT" && as_web php flarum cache:clear)
    systemctl restart "$PHP_FPM_SERVICE" nginx
    curl --fail --silent --show-error --retry 10 --retry-delay 1 \
        http://127.0.0.1:18080/ >/dev/null
}

verify_runtime() {
    local label="$1"
    local output_dir="$2"
    local expected_version="$3"
    local actual_version

    actual_version="$(core_version)"
    [[ "$actual_version" == "$expected_version" ]] ||
        die "expected Flarum $expected_version, found $actual_version"
    systemctl is-active --quiet nginx
    systemctl is-active --quiet "$PHP_FPM_SERVICE"
    systemctl is-active --quiet mariadb
    curl --fail --silent --show-error http://127.0.0.1:18080/ >/dev/null
    [[ -s "$APP_ROOT/public/assets/forum-ko.js" ]] || die "Korean locale bundle is missing"
    ! grep -Fq 'addTranslations([])' "$APP_ROOT/public/assets/forum-ko.js" ||
        die "Korean locale bundle is empty"
    grep -Fq 'core.forum.header.search_placeholder' "$APP_ROOT/public/assets/forum-ko.js" ||
        die "Korean core translations are missing"
    if [[ "$expected_version" == "$TARGET_VERSION" ]]; then
        [[ "$(package_version flarum/nicknames)" == "$NICKNAMES_VERSION" ]] ||
            die "flarum/nicknames security fix is missing"
        [[ "$(package_version symfony/mailer)" == "$MAILER_VERSION" ]] ||
            die "unexpected symfony/mailer compatibility pin"
        local audit_file="$output_dir/composer-audit-$label.json"
        (cd "$APP_ROOT" && as_web composer audit --locked --no-dev --format=json) \
            > "$audit_file" || true
        php -r '
            $data = json_decode(file_get_contents($argv[1]), true);
            $advisories = $data["advisories"] ?? [];
            if (isset($advisories["flarum/nicknames"])) {
                fwrite(STDERR, "flarum/nicknames advisory remains\n");
                exit(1);
            }
            $allowed = $advisories["symfony/mailer"] ?? [];
            unset($advisories["symfony/mailer"]);
            if ($advisories !== [] || count($allowed) !== 1 || ($allowed[0]["cve"] ?? "") !== "CVE-2026-45068") {
                fwrite(STDERR, "unexpected Composer security advisory set\n");
                exit(1);
            }
        ' "$audit_file"
    fi
    record_state "$label" "$output_dir"
}

snapshot() {
    local output_dir="$1"
    [[ ! -e "$output_dir" ]] || die "cycle already exists: $output_dir"
    install -d -m 0750 "$output_dir" "$output_dir/baseline-app"
    rsync -a --delete "$APP_ROOT/" "$output_dir/baseline-app/"
    mariadb-dump --single-transaction --quick --skip-lock-tables --hex-blob \
        --default-character-set=utf8mb4 "$DB_NAME" |
        gzip -1 > "$output_dir/baseline.sql.gz"
    gzip -t "$output_dir/baseline.sql.gz"
    chmod 0600 "$output_dir/baseline.sql.gz"
    verify_runtime baseline "$output_dir" 1.8.10
}

preflight() {
    local output_dir="$1"
    local dry_run_status=0
    (cd "$APP_ROOT" && as_web composer why-not flarum/core "$TARGET_VERSION") \
        > "$output_dir/composer-why-not.txt" 2>&1 || true
    (cd "$APP_ROOT" && as_web composer require \
        "flarum/core:$TARGET_VERSION" \
        "flarum/nicknames:$NICKNAMES_VERSION" \
        --no-update --no-interaction)
    (cd "$APP_ROOT" && as_web composer update \
        flarum/core flarum/nicknames --with-all-dependencies \
        --no-dev --prefer-dist --no-interaction --dry-run) \
        > "$output_dir/composer-dry-run.txt" 2>&1 || dry_run_status=$?
    rsync -a --delete "$output_dir/baseline-app/" "$APP_ROOT/"
    return "$dry_run_status"
}

upgrade() {
    local output_dir="$1"
    systemctl stop nginx
    (cd "$APP_ROOT" && as_web composer require \
        "flarum/core:$TARGET_VERSION" \
        "flarum/nicknames:$NICKNAMES_VERSION" \
        --no-update --no-interaction)
    (cd "$APP_ROOT" && as_web composer update \
        flarum/core flarum/nicknames --with-all-dependencies \
        --no-dev --prefer-dist --no-interaction) \
        > "$output_dir/composer-update.txt" 2>&1
    (cd "$APP_ROOT" && as_web php flarum migrate --no-interaction) \
        > "$output_dir/flarum-migrate.txt" 2>&1
    rebuild_runtime
    verify_runtime upgraded "$output_dir" "$TARGET_VERSION"
}

rollback() {
    local output_dir="$1"
    local baseline_state="$output_dir/state-baseline.tsv"
    [[ -d "$output_dir/baseline-app" && -s "$output_dir/baseline.sql.gz" ]] ||
        die "baseline snapshot is incomplete: $output_dir"

    systemctl stop nginx "$PHP_FPM_SERVICE"
    rsync -a --delete "$output_dir/baseline-app/" "$APP_ROOT/"
    mariadb -e "DROP DATABASE IF EXISTS $DB_NAME; CREATE DATABASE $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; GRANT ALL PRIVILEGES ON $DB_NAME.* TO 'www-data'@'localhost'; FLUSH PRIVILEGES;"
    gzip -dc "$output_dir/baseline.sql.gz" | mariadb "$DB_NAME"
    rebuild_runtime
    verify_runtime rollback "$output_dir" 1.8.10
    awk -F '\t' '
        NR == FNR {
            if ($1 != "database_sha256") expected[$1] = 1;
            next
        }
        expected[$1]
    ' \
        "$baseline_state" "$output_dir/state-rollback.tsv" \
        > "$output_dir/state-rollback-comparable.tsv"
    awk -F '\t' '$1 != "database_sha256"' "$baseline_state" \
        > "$output_dir/state-baseline-comparable.tsv"
    diff -u "$output_dir/state-baseline-comparable.tsv" "$output_dir/state-rollback-comparable.tsv" \
        > "$output_dir/rollback-state.diff"
}

main() {
    local command="${1:-}"
    local cycle_id="${2:-}"
    [[ -n "$command" && -n "$cycle_id" ]] || {
        usage
        exit 2
    }
    validate_environment
    trap restore_services EXIT
    local output_dir
    output_dir="$(cycle_dir "$cycle_id")"

    case "$command" in
        snapshot)
            snapshot "$output_dir"
            ;;
        preflight)
            [[ -d "$output_dir" ]] || die "unknown cycle: $cycle_id"
            preflight "$output_dir"
            ;;
        upgrade)
            [[ -d "$output_dir" ]] || die "unknown cycle: $cycle_id"
            upgrade "$output_dir"
            ;;
        verify)
            [[ -d "$output_dir" ]] || die "unknown cycle: $cycle_id"
            verify_runtime manual "$output_dir" "$(core_version)"
            ;;
        rollback)
            rollback "$output_dir"
            ;;
        cycle)
            snapshot "$output_dir"
            preflight "$output_dir"
            upgrade "$output_dir"
            rollback "$output_dir"
            ;;
        *)
            usage
            exit 2
            ;;
    esac
}

main "$@"
