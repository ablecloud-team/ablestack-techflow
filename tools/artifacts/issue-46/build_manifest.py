#!/usr/bin/env python3
"""Build the Issue #46 artifact inventory and SHA-256 checksums."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "output/issue-46-artifact-manifest.json"
ARTIFACTS = [
    "services/ai-gateway/app/data/golden-set-v1.json",
    "services/ai-gateway/app/evaluation.py",
    "services/ai-gateway/scripts/run_golden_evaluation.py",
    "services/ai-gateway/openapi/techflow-ai-gateway-v1.json",
    "services/ai-gateway/migrations/0007_reindex_fk_performance_up.sql",
    "services/ai-gateway/migrations/0007_reindex_fk_performance_down.sql",
    "services/ai-gateway/migrations/manifest.json",
    "deploy/compose/ai-gateway/.env.example",
    "deploy/compose/ai-gateway/compose.openai.override.yml",
    "deploy/compose/activepieces/flows/rag-orchestration-v1.json",
    "docs/decisions/techflow-golden-evaluation.json",
    "docs/decisions/techflow-parser-embedding-retrieval.json",
    "docs/runbooks/golden-set-quality-security-e2e.md",
    "docs/reports/issue-46-golden-set-quality-security-e2e-validation.md",
    "output/issue-46-reference-evaluation.json",
    "output/issue-46-live-evaluation.json",
    "output/issue-46-server-evidence.json",
    "output/presentation/techflow-golden-set-quality-security-e2e.pptx",
    "output/pdf/techflow-golden-set-quality-security-e2e-presentation.pdf",
    "output/pdf/techflow-golden-set-quality-security-e2e-report.pdf",
    "tools/artifacts/issue-46/build_golden_set.py",
    "tools/artifacts/issue-46/apply_codex_review.py",
    "tools/artifacts/issue-46/build_markdown_report.py",
    "tools/artifacts/issue-46/build_report.py",
    "tools/artifacts/issue-46/build_presentation.mjs",
    "tools/artifacts/issue-46/build_presentation_pdf.py",
    "tools/artifacts/issue-46/validate_artifacts.py",
    "tools/artifacts/issue-46/remote_exec.py",
    "tools/artifacts/issue-46/server_api.py",
    "tools/artifacts/issue-46/send_evaluation_event.py",
    "tools/artifacts/issue-46/reindex_active_sources.py",
    "tools/ai_gateway/validate_issue_46.py",
]


items = []
for relative in ARTIFACTS:
    path = ROOT / relative
    if not path.is_file():
        raise SystemExit(f"missing artifact: {relative}")
    body = path.read_bytes()
    items.append({"path": relative, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()})

payload = {
    "schemaVersion": "1.0",
    "issue": 46,
    "generatedAt": datetime.now(timezone.utc).isoformat(),
    "artifactCount": len(items),
    "artifacts": items,
}
OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(OUTPUT)
