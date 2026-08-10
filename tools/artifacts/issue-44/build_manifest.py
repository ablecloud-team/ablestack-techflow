#!/usr/bin/env python3
"""Build the Issue #44 artifact integrity manifest."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FILES = [
    "README.md",
    "docs/adr/0009-openai-runtime-integration.md",
    "docs/decisions/techflow-grounded-responses.json",
    "docs/runbooks/grounded-responses.md",
    "docs/reports/issue-44-grounded-responses-validation.md",
    "services/ai-gateway/README.md",
    "services/ai-gateway/pyproject.toml",
    "services/ai-gateway/app/__init__.py",
    "services/ai-gateway/app/config.py",
    "services/ai-gateway/app/main.py",
    "services/ai-gateway/app/models.py",
    "services/ai-gateway/app/postgres_store.py",
    "services/ai-gateway/app/provider.py",
    "services/ai-gateway/app/responses.py",
    "services/ai-gateway/app/store.py",
    "services/ai-gateway/openapi/techflow-ai-gateway-v1.json",
    "services/ai-gateway/scripts/issue44_canary.py",
    "services/ai-gateway/tests/test_api.py",
    "services/ai-gateway/tests/test_config.py",
    "services/ai-gateway/tests/test_responses.py",
    "deploy/compose/ai-gateway/.env.example",
    "deploy/compose/ai-gateway/compose.yml",
    "deploy/compose/ai-gateway/scripts/verify_runtime.py",
    "tools/ai_gateway/validate_issue_44.py",
    "tools/artifacts/issue-44/README.md",
    "tools/artifacts/issue-44/build_manifest.py",
    "tools/artifacts/issue-44/build_presentation_pdf.py",
    "tools/artifacts/issue-44/build_report.py",
    "tools/artifacts/issue-44/validate_artifacts.py",
    "output/pdf/techflow-grounded-responses-report.pdf",
    "output/pdf/techflow-grounded-responses-presentation.pdf",
    "output/presentation/techflow-grounded-responses.pptx",
]


def canonical(path: Path) -> bytes:
    data = path.read_bytes()
    if path.suffix.lower() in {".pdf", ".pptx"}:
        return data
    return data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


items = []
for value in FILES:
    path = ROOT / value
    content = canonical(path)
    items.append({"path": value, "size": len(content), "sha256": hashlib.sha256(content).hexdigest().upper()})
output = ROOT / "output/issue-44-artifact-manifest.json"
output.write_text(json.dumps({
    "schemaVersion": "1.0", "issue": 44, "status": "implemented-deployed-and-validated",
    "gatewayVersion": "0.4.0", "files": items,
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(output)
