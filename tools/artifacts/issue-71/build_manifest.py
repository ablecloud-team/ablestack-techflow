#!/usr/bin/env python3
"""Build the Issue #71 artifact manifest."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "output/issue-71-flarum-upgrade-artifact-manifest.json"
ARTIFACTS = [
    "deploy/flarum/rehearse-1.8.18.sh",
    "docs/evidence/issue-71/flarum-1.8.18-validation.json",
    "docs/runbooks/flarum-1.8.18-upgrade-rollback.md",
    "docs/reports/issue-71-flarum-1.8.18-validation.md",
    "output/pdf/techflow-flarum-1.8.18-upgrade-report.pdf",
    "output/presentation/techflow-flarum-1.8.18-upgrade.pptx",
    "output/pdf/techflow-flarum-1.8.18-upgrade-presentation.pdf",
    "tools/artifacts/issue-71/README.md",
    "tools/artifacts/issue-71/build_report.py",
    "tools/artifacts/issue-71/build_presentation.mjs",
    "tools/artifacts/issue-71/build_presentation_pdf.py",
    "tools/artifacts/issue-71/build_manifest.py",
    "tools/artifacts/issue-71/validate_artifacts.py"
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
    "issue": 71,
    "generatedAt": datetime.now(timezone.utc).isoformat(),
    "artifactCount": len(items),
    "artifacts": items,
}
OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(OUTPUT)
