#!/usr/bin/env python3
"""Repository-level validation for Issue #41 implementation assets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services" / "ai-gateway"
DEPLOY = ROOT / "deploy" / "compose" / "ai-gateway"
EXPECTED_OPERATIONS = {
    ("get", "/healthz"),
    ("post", "/v1/sources"),
    ("get", "/v1/sources/{sourceId}"),
    ("post", "/v1/compatibility-sets"),
    ("post", "/v1/sources/{sourceId}/approve"),
    ("post", "/v1/sources/{sourceId}/ingestions"),
    ("delete", "/v1/sources/{sourceId}"),
    ("get", "/v1/jobs/{jobId}"),
    ("post", "/v1/rag/query"),
    ("post", "/v1/evaluations/runs"),
    ("get", "/v1/evaluations/runs/{runId}"),
}
EXPECTED_TABLES = {
    "rag_source", "rag_source_version", "rag_compatibility_set", "rag_compatibility_set_source",
    "rag_ingestion_job", "rag_chunk", "rag_embedding_profile", "rag_chunk_embedding",
    "rag_code_symbol", "rag_code_relation", "rag_deletion_ledger", "rag_evaluation_case",
    "rag_evaluation_run", "rag_evaluation_result", "rag_provider_call",
}


def validate() -> list[str]:
    errors: list[str] = []
    openapi = json.loads((SERVICE / "openapi" / "techflow-ai-gateway-v1.json").read_text(encoding="utf-8"))
    operations = {
        (method.lower(), path)
        for path, methods in openapi.get("paths", {}).items()
        for method in methods
        if method.lower() in {"get", "post", "delete", "put", "patch"}
    }
    if not EXPECTED_OPERATIONS.issubset(operations):
        errors.append(f"Issue #41 OpenAPI operations missing: {sorted(EXPECTED_OPERATIONS - operations)}")

    up = (SERVICE / "migrations" / "0001_schema_up.sql").read_text(encoding="utf-8")
    tables = set(re.findall(r"(?im)^CREATE TABLE\s+(rag_[a-z_]+)", up))
    if tables != EXPECTED_TABLES:
        errors.append(f"migration tables mismatch: {sorted(tables ^ EXPECTED_TABLES)}")
    provider_block = up.split("CREATE TABLE rag_provider_call", 1)[1].split(");", 1)[0].lower()
    if any(value in provider_block for value in ("prompt ", "response ", "authorization", "api_key", "credential", "content ")):
        errors.append("provider call table contains prohibited raw-content fields")

    manifest_path = SERVICE / "migrations" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for item in manifest.get("files", []):
        path = SERVICE / "migrations" / item["path"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            errors.append(f"migration checksum mismatch: {item['path']}")

    provider = (SERVICE / "app" / "provider.py").read_text(encoding="utf-8")
    for required in (
        "OPENAI_RAG_DEFAULT_V1", "gpt-5.6-terra", "OPENAI_RAG_ESCALATION_V1", "gpt-5.6-sol",
        "OPENAI_EMBEDDING_V1", "text-embedding-3-large", "embedding_dimension=3072",
    ):
        if required not in provider:
            errors.append(f"provider profile missing: {required}")

    dockerfile = (SERVICE / "Dockerfile").read_text(encoding="utf-8")
    compose = (DEPLOY / "compose.yml").read_text(encoding="utf-8")
    if not re.search(r"^FROM .+@sha256:[0-9a-f]{64}$", dockerfile, re.MULTILINE):
        errors.append("gateway base image is not digest pinned")
    for required in ("read_only: true", "cap_drop:", "internal: true", "rag_edge:", "TECHFLOW_RAG_PROVIDER_MODE: mock"):
        if required not in compose:
            errors.append(f"compose boundary missing: {required}")
    if "OPENAI_API_KEY" in compose:
        errors.append("real OpenAI key must not be configured in Issue #41")

    tracked_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for base in (SERVICE, DEPLOY)
        for path in base.rglob("*")
        if path.is_file() and path.suffix.lower() in {".py", ".sql", ".yml", ".yaml", ".toml", ".lock", ".sh", ".example"}
    )
    secret_patterns = [
        r"ghp_[A-Za-z0-9]{20,}",
        r"sk-[A-Za-z0-9_-]{20,}",
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    ]
    if any(re.search(pattern, tracked_text) for pattern in secret_patterns):
        errors.append("secret-like value detected")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("issue41=valid apiFoundation=11 tables=15 profiles=3 providerCalls=mock secrets=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
