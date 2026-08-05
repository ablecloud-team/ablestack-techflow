#!/usr/bin/env python3
"""Build the Issue #43 artifact integrity manifest."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FILES = [
    "README.md",
    "docs/decisions/techflow-parser-embedding-retrieval.json",
    "docs/runbooks/parser-embedding-retrieval.md",
    "docs/reports/issue-43-parser-embedding-validation.md",
    "services/ai-gateway/README.md",
    "services/ai-gateway/Dockerfile",
    "services/ai-gateway/app/chunking.py",
    "services/ai-gateway/app/embedding.py",
    "services/ai-gateway/app/indexing.py",
    "services/ai-gateway/app/main.py",
    "services/ai-gateway/app/models.py",
    "services/ai-gateway/app/postgres_store.py",
    "services/ai-gateway/app/store.py",
    "services/ai-gateway/migrations/0005_parser_embedding_retrieval_up.sql",
    "services/ai-gateway/migrations/0005_parser_embedding_retrieval_down.sql",
    "services/ai-gateway/migrations/manifest.json",
    "services/ai-gateway/openapi/techflow-ai-gateway-v1.json",
    "services/ai-gateway/scripts/issue43_canary.py",
    "services/ai-gateway/scripts/prefetch_parsers.py",
    "tools/ai_gateway/validate_issue_43.py",
    "tools/artifacts/issue-43/README.md",
    "tools/artifacts/issue-43/build_presentation.mjs",
    "tools/artifacts/issue-43/build_presentation_pdf.py",
    "tools/artifacts/issue-43/build_report.py",
    "tools/artifacts/issue-43/deviation-log.txt",
    "tools/artifacts/issue-43/template-audit.txt",
    "tools/artifacts/issue-43/template-frame-map.json",
    "tools/artifacts/issue-43/validate_artifacts.py",
    "output/pdf/techflow-parser-embedding-report.pdf",
    "output/pdf/techflow-parser-embedding-presentation.pdf",
    "output/presentation/techflow-parser-embedding.pptx",
]


def canonical(path):
    data = path.read_bytes()
    if path.suffix.lower() in {".pdf", ".pptx"}:
        return data
    return data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


items = []
for value in FILES:
    path = ROOT / value
    content = canonical(path)
    items.append({"path": value, "size": len(content), "sha256": hashlib.sha256(content).hexdigest().upper()})
output = ROOT / "output/issue-43-artifact-manifest.json"
output.write_text(json.dumps({
    "schemaVersion": "1.0", "issue": 43, "status": "implemented-deployed-and-validated",
    "initialSourceReviewer": "dhslove", "sourceProfileId": "GENIE_MASTER",
    "sourceCommit": "3e3c5c364f5c7261b07d49fcbcd4f3605b91f3b1", "files": items,
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(output)
