#!/usr/bin/env sh
set -eu

if [ "${TECHFLOW_RAG_STORE:-memory}" = "postgres" ] && [ -z "${TECHFLOW_RAG_DATABASE_DSN:-}" ]; then
    : "${TECHFLOW_RAG_DATABASE_PASSWORD_FILE:?database password file is required}"
    : "${TECHFLOW_RAG_DATABASE_HOST:?database host is required}"
    : "${TECHFLOW_RAG_DATABASE_NAME:?database name is required}"
    : "${TECHFLOW_RAG_DATABASE_USER:?database user is required}"
    export TECHFLOW_RAG_DATABASE_DSN="$(python -c 'import os, pathlib, urllib.parse; password=pathlib.Path(os.environ["TECHFLOW_RAG_DATABASE_PASSWORD_FILE"]).read_text(encoding="utf-8").strip(); print("postgresql://{}:{}@{}:{}/{}".format(urllib.parse.quote(os.environ["TECHFLOW_RAG_DATABASE_USER"], safe=""), urllib.parse.quote(password, safe=""), os.environ["TECHFLOW_RAG_DATABASE_HOST"], os.environ.get("TECHFLOW_RAG_DATABASE_PORT", "5432"), urllib.parse.quote(os.environ["TECHFLOW_RAG_DATABASE_NAME"], safe="")))')"
fi

exec "$@"
