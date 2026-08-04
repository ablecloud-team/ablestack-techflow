#!/usr/bin/env bash
set -euo pipefail
set +x

escape_password() {
  local value
  value="$(tr -d '\r\n' < "$1")"
  printf '%s' "${value//\'/\'\'}"
}

app_password="$(escape_password /run/secrets/app_password)"
migration_password="$(escape_password /run/secrets/migration_password)"
fetcher_password="$(escape_password /run/secrets/fetcher_password)"

{
  printf "DO \$\$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='techflow_rag_app_login') THEN CREATE ROLE techflow_rag_app_login LOGIN INHERIT; END IF; END \$\$;\n"
  printf "DO \$\$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='techflow_rag_migration_login') THEN CREATE ROLE techflow_rag_migration_login LOGIN INHERIT; END IF; END \$\$;\n"
  printf "DO \$\$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='techflow_rag_fetcher_login') THEN CREATE ROLE techflow_rag_fetcher_login LOGIN INHERIT; END IF; END \$\$;\n"
  printf "ALTER ROLE techflow_rag_app_login PASSWORD '%s';\n" "$app_password"
  printf "ALTER ROLE techflow_rag_migration_login PASSWORD '%s';\n" "$migration_password"
  printf "ALTER ROLE techflow_rag_fetcher_login PASSWORD '%s';\n" "$fetcher_password"
  printf "GRANT techflow_rag_app TO techflow_rag_app_login;\n"
  printf "GRANT techflow_rag_migrator TO techflow_rag_migration_login;\n"
  printf "GRANT techflow_rag_source_fetcher TO techflow_rag_fetcher_login;\n"
} | psql --set=ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB"

unset app_password migration_password fetcher_password
