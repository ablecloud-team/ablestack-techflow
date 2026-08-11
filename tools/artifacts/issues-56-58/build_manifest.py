#!/usr/bin/env python3
"""Build the reproducible artifact manifest for Issues #56-#58."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "output" / "issues-56-58-artifact-manifest.json"

ASSETS = (
    "README.md",
    "deploy/compose/activepieces/flows/assist-orchestration-v1.json",
    "docs/plans/issues-56-58-assist-multimodal-design.md",
    "docs/reports/issues-56-58-assist-multimodal-validation.md",
    "docs/runbooks/assist-multimodal.md",
    "services/ai-gateway/app/artifacts.py",
    "services/ai-gateway/app/comprehensive.py",
    "services/ai-gateway/app/main.py",
    "services/ai-gateway/app/responses.py",
    "services/ai-gateway/app/data/comprehensive-golden-set-v1.json",
    "services/ai-gateway/app/data/multimodal-golden-set-v1.json",
    "services/ai-gateway/app/data/golden-artifacts/synthetic-vm-error.png",
    "services/ai-gateway/openapi/techflow-ai-gateway-v1.json",
    "output/issues-56-58-reference-evaluation.json",
    "output/issues-56-58-live-evaluation.json",
    "output/pdf/techflow-assist-multimodal-report.pdf",
    "output/pdf/techflow-assist-multimodal-presentation.pdf",
    "output/presentation/techflow-assist-multimodal.pptx",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    missing = [relative for relative in ASSETS if not (ROOT / relative).is_file()]
    if missing:
        raise SystemExit(f"missing assets: {', '.join(missing)}")

    files = []
    for relative in ASSETS:
        path = ROOT / relative
        files.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": digest(path),
            }
        )

    manifest = {
        "schemaVersion": "1.0",
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "scope": ["issue-56", "issue-57", "issue-58"],
        "files": files,
    }
    OUTPUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"manifest={OUTPUT.relative_to(ROOT)} files={len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
