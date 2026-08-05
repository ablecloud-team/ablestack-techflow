#!/usr/bin/env python3
"""Create the checksum manifest for Issue #42 assets."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FILES = [
    ROOT / "README.md",
    ROOT / "docs/plans/techflow-product-roadmap.md",
    ROOT / "docs/decisions/techflow-source-registry.json",
    ROOT / "docs/runbooks/rag-poc-development.md",
    ROOT / "docs/runbooks/source-registry-quarantine.md",
    ROOT / "docs/reports/issue-42-source-registry-validation.md",
    ROOT / "services/ai-gateway/README.md",
    ROOT / "services/ai-gateway/app/source_registry.py",
    ROOT / "services/ai-gateway/app/source_fetcher.py",
    ROOT / "services/ai-gateway/app/source_policy.py",
    ROOT / "services/ai-gateway/app/source_pipeline.py",
    ROOT / "services/ai-gateway/migrations/0002_source_registry_up.sql",
    ROOT / "services/ai-gateway/migrations/0002_source_registry_down.sql",
    ROOT / "services/ai-gateway/openapi/techflow-ai-gateway-v1.json",
    ROOT / "deploy/compose/ai-gateway/compose.yml",
    ROOT / "deploy/compose/activepieces/flows/rag-source-discovery-v1.json",
    ROOT / "deploy/compose/activepieces/flows/rag-source-review-index-v1.json",
    ROOT / "tools/ai_gateway/validate_issue_42.py",
    ROOT / "tools/ai_gateway/test_validate_issue_42.py",
    ROOT / "tools/artifacts/issue-42/build_presentation.mjs",
    ROOT / "tools/artifacts/issue-42/build_report.py",
    ROOT / "tools/artifacts/issue-42/validate_artifacts.py",
    ROOT / "output/pdf/techflow-source-registry-report.pdf",
    ROOT / "output/pdf/techflow-source-registry-presentation.pdf",
    ROOT / "output/presentation/techflow-source-registry.pptx",
]
BINARY = {".pdf", ".pptx"}


def canonical(path):
    data = path.read_bytes()
    if path.suffix.lower() in BINARY:
        return data, "binary-raw"
    text = data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return text.encode("utf-8"), "text-lf-normalized"


def record(path):
    content, mode = canonical(path)
    return {"path": path.relative_to(ROOT).as_posix(), "size": len(content), "sha256": hashlib.sha256(content).hexdigest().upper(), "contentMode": mode}


missing = [str(path) for path in FILES if not path.exists()]
if missing:
    raise FileNotFoundError(f"missing artifacts: {missing}")
manifest = {
    "schemaVersion": "1.0",
    "issue": 42,
    "title": "Source Registry·검역·승인 파이프라인 구현",
    "status": "implemented-deployed-and-validated",
    "initialSourceReviewer": "dhslove",
    "generatedAt": "2026-08-05T12:00:00+09:00",
    "hashPolicy": "binary raw bytes; UTF-8 text normalized to LF",
    "files": [record(path) for path in FILES],
}
output = ROOT / "output/issue-42-artifact-manifest.json"
output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(output)
