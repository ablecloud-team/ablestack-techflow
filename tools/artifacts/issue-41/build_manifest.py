#!/usr/bin/env python3
"""Create the checksum manifest for Issue #41 implementation assets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FILES = [
    ROOT / "README.md",
    ROOT / "docs/plans/techflow-product-roadmap.md",
    ROOT / "docs/decisions/techflow-ai-gateway-foundation.json",
    ROOT / "docs/runbooks/ai-gateway-foundation.md",
    ROOT / "docs/reports/issue-41-ai-gateway-foundation-validation.md",
    ROOT / "services/ai-gateway/README.md",
    ROOT / "services/ai-gateway/openapi/techflow-ai-gateway-v1.json",
    ROOT / "deploy/compose/ai-gateway/compose.yml",
    ROOT / "tools/ai_gateway/validate_issue_41.py",
    ROOT / "tools/ai_gateway/test_validate_issue_41.py",
    ROOT / "tools/artifacts/issue-41/build_manifest.py",
    ROOT / "tools/artifacts/issue-41/validate_artifacts.py",
    ROOT / "output/pdf/techflow-ai-gateway-foundation-report.pdf",
    ROOT / "output/pdf/techflow-ai-gateway-foundation-presentation.pdf",
    ROOT / "output/presentation/techflow-ai-gateway-foundation.pptx",
]
BINARY_SUFFIXES = {".pdf", ".pptx"}


def canonical(path: Path) -> tuple[bytes, str]:
    data = path.read_bytes()
    if path.suffix.lower() in BINARY_SUFFIXES:
        return data, "binary-raw"
    text = data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return text.encode("utf-8"), "text-lf-normalized"


def record(path: Path) -> dict[str, object]:
    content, mode = canonical(path)
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "size": len(content),
        "sha256": hashlib.sha256(content).hexdigest().upper(),
        "contentMode": mode,
    }


missing = [str(path) for path in FILES if not path.exists()]
if missing:
    raise FileNotFoundError(f"missing artifacts: {missing}")
manifest = {
    "schemaVersion": "1.0",
    "issue": 41,
    "title": "AI Gateway API·DB·Mock Provider 기반 구현",
    "status": "implemented-and-validated",
    "generatedAt": "2026-08-04T12:00:00+09:00",
    "hashPolicy": "binary raw bytes; UTF-8 text normalized to LF",
    "files": [record(path) for path in FILES],
}
output = ROOT / "output/issue-41-artifact-manifest.json"
output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(output)
