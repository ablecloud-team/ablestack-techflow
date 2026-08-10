#!/usr/bin/env python3
"""Build the Issue #45 artifact integrity manifest."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FILES = [
    "README.md",
    "docs/plans/techflow-product-roadmap.md",
    "docs/decisions/techflow-activepieces-rag-orchestration.json",
    "docs/runbooks/activepieces-rag-orchestration.md",
    "docs/reports/issue-45-activepieces-rag-orchestration-validation.md",
    "deploy/compose/activepieces/.env.example",
    "deploy/compose/activepieces/compose.yml",
    "deploy/compose/activepieces/image-lock.json",
    "deploy/compose/activepieces/event-gateway/Dockerfile",
    "deploy/compose/activepieces/event-gateway/gateway.py",
    "deploy/compose/activepieces/event-gateway/test_gateway.py",
    "deploy/compose/activepieces/flows/rag-orchestration-v1.json",
    "deploy/compose/activepieces/scripts/manage-rag-flows.py",
    "deploy/compose/activepieces/scripts/test_manage_rag_flows.py",
    "deploy/compose/ai-gateway/compose.yml",
    "services/ai-gateway/README.md",
    "services/ai-gateway/pyproject.toml",
    "services/ai-gateway/app/__init__.py",
    "services/ai-gateway/app/main.py",
    "services/ai-gateway/app/postgres_store.py",
    "services/ai-gateway/app/store.py",
    "services/ai-gateway/migrations/0006_orchestration_correlation_up.sql",
    "services/ai-gateway/migrations/0006_orchestration_correlation_down.sql",
    "services/ai-gateway/migrations/manifest.json",
    "services/ai-gateway/openapi/techflow-ai-gateway-v1.json",
    "services/ai-gateway/scripts/migrate.py",
    "services/ai-gateway/tests/test_api.py",
    "services/ai-gateway/tests/test_container_contract.py",
    "services/ai-gateway/tests/test_migrations.py",
    "tools/artifacts/issue-45/README.md",
    "tools/artifacts/issue-45/build_report.py",
    "tools/artifacts/issue-45/build_presentation_pdf.py",
    "tools/artifacts/issue-45/build_manifest.py",
    "tools/artifacts/issue-45/validate_artifacts.py",
    "output/pdf/techflow-activepieces-rag-orchestration-report.pdf",
    "output/pdf/techflow-activepieces-rag-orchestration-presentation.pdf",
    "output/presentation/techflow-activepieces-rag-orchestration.pptx"
]


def canonical(path: Path) -> bytes:
    data = path.read_bytes()
    if path.suffix.lower() in {".pdf", ".pptx"}:
        return data
    return data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


items = []
for value in FILES:
    content = canonical(ROOT / value)
    items.append({"path": value, "size": len(content), "sha256": hashlib.sha256(content).hexdigest().upper()})
output = ROOT / "output/issue-45-artifact-manifest.json"
output.write_text(json.dumps({
    "schemaVersion": "1.0", "issue": 45, "status": "implemented-deployed-and-validated",
    "aiGatewayVersion": "0.5.0", "eventGatewayVersion": "0.3.0", "files": items,
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(output)
