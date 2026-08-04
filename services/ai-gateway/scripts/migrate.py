#!/usr/bin/env python3
"""Apply or roll back the Issue #41 schema without printing credentials."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "migrations"
EXPECTED_TABLES = {
    "rag_source", "rag_source_version", "rag_compatibility_set", "rag_compatibility_set_source",
    "rag_ingestion_job", "rag_chunk", "rag_embedding_profile", "rag_chunk_embedding",
    "rag_code_symbol", "rag_code_relation", "rag_deletion_ledger", "rag_evaluation_case",
    "rag_evaluation_run", "rag_evaluation_result", "rag_provider_call",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("direction", choices=("up", "down", "verify"))
    parser.add_argument("--allow-destructive-rollback", action="store_true")
    return parser.parse_args()


def dsn() -> str:
    value = os.getenv("TECHFLOW_RAG_MIGRATION_DSN") or os.getenv("TECHFLOW_RAG_DATABASE_DSN")
    if not value:
        raise SystemExit("migration DSN is required through runtime environment injection")
    return value


def table_names(connection: psycopg.Connection) -> set[str]:
    rows = connection.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'rag_%'"
    ).fetchall()
    return {row[0] for row in rows}


def verify(connection: psycopg.Connection) -> None:
    actual = table_names(connection)
    if actual != EXPECTED_TABLES:
        raise SystemExit(f"schema mismatch expected=15 actual={len(actual)}")
    extensions = {row[0] for row in connection.execute(
        "SELECT extname FROM pg_extension WHERE extname IN ('vector', 'pg_trgm')"
    ).fetchall()}
    if extensions != {"vector", "pg_trgm"}:
        raise SystemExit("required extensions are missing")
    print("schema=valid tables=15 extensions=2")


def main() -> int:
    args = parse_args()
    with psycopg.connect(dsn(), autocommit=False) as connection:
        connection.execute("SELECT pg_advisory_xact_lock(82410041)")
        if args.direction == "verify":
            verify(connection)
            return 0
        if args.direction == "down":
            if not args.allow_destructive_rollback:
                raise SystemExit("--allow-destructive-rollback is required")
            connection.execute((MIGRATIONS / "0001_schema_down.sql").read_text(encoding="utf-8"))
            print("schema=rolled-back")
            return 0
        connection.execute((MIGRATIONS / "0000_extensions_roles_up.sql").read_text(encoding="utf-8"))
        actual = table_names(connection)
        if not actual:
            connection.execute((MIGRATIONS / "0001_schema_up.sql").read_text(encoding="utf-8"))
        verify(connection)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
