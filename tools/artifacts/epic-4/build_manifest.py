#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "output/epic-4-assist-validation-artifact-manifest.json"
FILES = [
    "docs/reports/epic4-assist-validation.md",
    "docs/runbooks/epic4-service-continuity.md",
    "docs/plans/epic5-assist-mvp-plan.md",
    "docs/evidence/epic-4/production-e2e.json",
    "output/pdf/techflow-epic4-assist-validation-report.pdf",
    "output/pdf/techflow-epic4-assist-validation-presentation.pdf",
    "output/presentation/techflow-epic4-assist-validation.pptx",
]

artifacts = []
for relative in FILES:
    path = ROOT / relative
    payload = path.read_bytes()
    artifacts.append({
        "path": relative,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    })

OUTPUT.write_text(json.dumps({
    "schemaVersion": 1,
    "epic": 4,
    "release": "0.15.0",
    "artifactCount": len(artifacts),
    "artifacts": artifacts,
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(OUTPUT)
