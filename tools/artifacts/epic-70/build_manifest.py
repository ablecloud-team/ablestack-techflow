#!/usr/bin/env python3
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "output/epic-70-community-modernization-artifact-manifest.json"
ARTIFACTS = [
    "docs/evidence/epic-70/community-modernization-e2e.json",
    "docs/evidence/epic-70/community-discussion-174.jpg",
    "docs/reports/epic-70-community-modernization-validation.md",
    "docs/runbooks/community-platform-integrated-e2e.md",
    "docs/presentations/epic-70-community-modernization.md",
    "output/pdf/techflow-community-modernization-report.pdf",
    "output/presentation/techflow-community-modernization.pptx",
    "output/pdf/techflow-community-modernization-presentation.pdf",
]
items = []
for relative in ARTIFACTS:
    path = ROOT / relative
    if not path.is_file():
        raise SystemExit(f"missing artifact: {relative}")
    body = path.read_bytes()
    items.append({"path": relative, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()})
OUTPUT.write_text(json.dumps({"schemaVersion":"1.0","epic":70,"generatedAt":datetime.now(timezone.utc).isoformat(),"artifactCount":len(items),"artifacts":items}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(OUTPUT)
