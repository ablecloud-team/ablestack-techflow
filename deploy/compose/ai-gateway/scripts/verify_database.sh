#!/usr/bin/env bash
set -euo pipefail

compose_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$compose_dir"

database_name="${TECHFLOW_RAG_DATABASE_NAME:-techflow_rag}"
result="$(docker compose --env-file .env exec -T database psql \
  --username techflow_bootstrap \
  --dbname "$database_name" \
  --tuples-only --no-align \
  --command "SELECT
    (SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'rag_%'),
    has_schema_privilege('techflow_rag_app', 'public', 'CREATE'),
    has_table_privilege('techflow_rag_app', 'public.rag_provider_call', 'SELECT'),
    has_table_privilege('techflow_rag_source_fetcher', 'public.rag_provider_call', 'SELECT'),
    (SELECT count(*) FROM pg_extension WHERE extname IN ('vector', 'pg_trgm'));" \
  | tr -d '[:space:]')"

test "$result" = "15|f|t|f|2" || {
  echo "database_contract=invalid result=$result" >&2
  exit 1
}

echo "database_contract=valid tables=15 app_schema_create=false app_provider_audit_select=true fetcher_provider_audit_select=false extensions=2"
