#!/usr/bin/env python3
"""Create a checksum manifest for Issue #11 artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = json.loads(
    (ROOT / "docs" / "decisions" / "activepieces-license-review.json").read_text(
        encoding="utf-8"
    )
)
FILES = [
    ROOT / "docs" / "decisions" / "activepieces-license-review.json",
    ROOT / "docs" / "decisions" / "activepieces-license-feature-matrix.md",
    ROOT / "output" / "pdf" / "activepieces-license-review-report.pdf",
    ROOT / "output" / "pdf" / "activepieces-license-review-presentation.pdf",
    ROOT / "output" / "presentation" / "activepieces-license-review.pptx",
]
OUTPUT = ROOT / "output" / "issue-11-artifact-manifest.json"


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest().upper()


missing = [str(path) for path in FILES if not path.exists()]
if missing:
    raise FileNotFoundError(f"Missing artifacts: {missing}")

manifest = {
    "schemaVersion": "1.0",
    "issue": DATA["issue"],
    "generatedAt": DATA["analysisDate"],
    "baseline": DATA["baseline"],
    "files": [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "size": path.stat().st_size,
            "sha256": digest(path),
        }
        for path in FILES
    ],
}
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(OUTPUT)
