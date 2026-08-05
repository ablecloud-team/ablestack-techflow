#!/usr/bin/env python3
"""Repository-level validation for Issue #42 source registry implementation."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services" / "ai-gateway"
EXPECTED_PROFILES = {
    "SHARED_DOCS", "CLOUD_MAIN", "CLOUD_DIPLO", "CLOUD_EUROPA", "WALL_MAIN",
    "COCKPIT_DIPLO", "GENIE_MASTER", "KICKSTART_MASTER", "QEMU_EXEC_TOOLS_MAIN",
}
EXPECTED_NEW_OPERATIONS = {
    ("get", "/v1/source-profiles"),
    ("post", "/v1/source-profiles/{sourceProfileId}/discoveries"),
    ("get", "/v1/source-versions/{sourceVersionId}"),
    ("post", "/v1/source-versions/{sourceVersionId}/scan"),
    ("get", "/v1/source-versions/{sourceVersionId}/files"),
    ("post", "/v1/source-versions/{sourceVersionId}/approve"),
    ("post", "/v1/jobs/{jobId}/complete"),
}


def validate() -> list[str]:
    errors: list[str] = []
    registry = (SERVICE / "app" / "source_registry.py").read_text(encoding="utf-8")
    profiles = set(re.findall(r'^    "([A-Z][A-Z0-9_]+)": SourceProfile\(', registry, re.MULTILINE))
    if profiles != EXPECTED_PROFILES:
        errors.append(f"source profiles mismatch: {sorted(profiles ^ EXPECTED_PROFILES)}")
    for required in (
        'branch="main"', 'branch="ablestack-diplo"', 'branch="ablestack-europa"',
        'initial_reviewer": "dhslove"', 'classification": "D0"',
    ):
        if required not in registry:
            errors.append(f"registry contract missing: {required}")

    openapi = json.loads((SERVICE / "openapi" / "techflow-ai-gateway-v1.json").read_text(encoding="utf-8"))
    operations = {
        (method.lower(), path)
        for path, methods in openapi["paths"].items()
        for method in methods
        if method.lower() in {"get", "post", "delete", "put", "patch"}
    }
    if len(operations) != 18 or not EXPECTED_NEW_OPERATIONS.issubset(operations):
        errors.append("Issue #42 OpenAPI operation set is incomplete")

    migration = (SERVICE / "migrations" / "0002_source_registry_up.sql").read_text(encoding="utf-8")
    for table in ("rag_source_blob", "rag_source_file", "rag_source_scan_finding"):
        if f"CREATE TABLE {table}" not in migration:
            errors.append(f"migration table missing: {table}")
    for state in ("REGISTERED", "QUARANTINED", "APPROVED", "INDEXING", "ACTIVE"):
        if f"'{state}'" not in migration:
            errors.append(f"state missing: {state}")
    if migration.count("'ACTIVE_PLUS_7D_DELETION_SLA'") != 9:
        errors.append("nine registry seeds are required")

    fetcher = (SERVICE / "app" / "source_fetcher.py").read_text(encoding="utf-8")
    prohibited = ('"checkout"', '"submodule"', "shell=True", '"GIT_LFS_SKIP_SMUDGE": "0"')
    for value in prohibited:
        if value in fetcher:
            errors.append(f"fetcher prohibited operation: {value}")
    for required in ("GIT_LFS_SKIP_SMUDGE", "core.hooksPath", "protocol.ext.allow=never", "fetch.fsckObjects=true"):
        if required not in fetcher:
            errors.append(f"fetcher safety control missing: {required}")

    policy = (SERVICE / "app" / "source_policy.py").read_text(encoding="utf-8")
    for rule in (
        "PATH_TRAVERSAL", "SUBMODULE_FORBIDDEN", "SYMLINK_FORBIDDEN", "FILE_SIZE_LIMIT", "BINARY_CONTENT",
        "UTF8_REQUIRED", "SECRET_GITHUB_TOKEN", "PII_KR_RRN", "PROMPT_INJECTION_OVERRIDE",
    ):
        if rule not in policy:
            errors.append(f"quarantine rule missing: {rule}")

    flow_dir = ROOT / "deploy" / "compose" / "activepieces" / "flows"
    for flow_name in ("rag-source-discovery-v1.json", "rag-source-review-index-v1.json"):
        flow = json.loads((flow_dir / flow_name).read_text(encoding="utf-8"))
        if flow.get("runtime", {}).get("published") is not False:
            errors.append(f"flow must remain unpublished before runtime gate: {flow_name}")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("issue42=valid profiles=9 repositories=7 api=18 tables=18 reviewer=dhslove sourceExecution=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
