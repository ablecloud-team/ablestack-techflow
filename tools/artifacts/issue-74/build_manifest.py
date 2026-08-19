#!/usr/bin/env python3
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "output/issue-74-community-operations-artifact-manifest.json"
ARTIFACTS = [
    "deploy/flarum/operations/community-ops-common.sh",
    "deploy/flarum/operations/community-backup.sh",
    "deploy/flarum/operations/community-verify-backup.sh",
    "deploy/flarum/operations/community-restore.sh",
    "deploy/flarum/operations/community-monitor.sh",
    "deploy/flarum/operations/community-offsite-export.sh",
    "deploy/flarum/operations/community-install.sh",
    "docs/adr/0010-community-backup-observability-security.md",
    "docs/runbooks/community-backup-monitor-security.md",
    "docs/reports/issue-74-community-operations-validation.md",
    "docs/presentations/issue-74-community-operations.md",
    "docs/evidence/issue-74/community-operations-validation.json",
    "output/pdf/techflow-community-operations-report.pdf",
    "output/presentation/techflow-community-operations.pptx",
    "output/pdf/techflow-community-operations-presentation.pdf",
    "tools/artifacts/issue-74/README.md",
    "tools/artifacts/issue-74/build_report.py",
    "tools/artifacts/issue-74/build_presentation.mjs",
    "tools/artifacts/issue-74/build_presentation_pdf.py",
    "tools/artifacts/issue-74/build_manifest.py",
    "tools/artifacts/issue-74/validate_artifacts.py",
]
items = []
for relative in ARTIFACTS:
    path = ROOT / relative
    if not path.is_file():
        raise SystemExit(f"missing artifact: {relative}")
    body = path.read_bytes()
    items.append({"path": relative, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()})
OUTPUT.write_text(json.dumps({"schemaVersion":"1.0","issue":74,"generatedAt":datetime.now(timezone.utc).isoformat(),"artifactCount":len(items),"artifacts":items}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(OUTPUT)
