#!/usr/bin/env python3
"""Create a checksum manifest for Issue #18 immutable release assets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = json.loads((ROOT / "docs" / "decisions" / "techflow-image-version-lock.json").read_text(encoding="utf-8"))
FILES = [
    ROOT / ".gitattributes",
    ROOT / "README.md",
    ROOT / "docs" / "adr" / "0005-techflow-image-version-lock.md",
    ROOT / "docs" / "decisions" / "techflow-image-version-lock.json",
    ROOT / "docs" / "reports" / "issue-18-image-digest-validation.md",
    ROOT / "docs" / "runbooks" / "image-version-upgrade-rollback.md",
    ROOT / "deploy" / "compose" / "activepieces" / ".env.example",
    ROOT / "deploy" / "compose" / "activepieces" / "README.md",
    ROOT / "deploy" / "compose" / "activepieces" / "compose.yml",
    ROOT / "deploy" / "compose" / "activepieces" / "image-lock.json",
    ROOT / "deploy" / "compose" / "activepieces" / "event-gateway" / "Dockerfile",
    ROOT / "deploy" / "compose" / "activepieces" / "event-gateway" / "gateway.py",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "release_lock.py",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "test_release_lock.py",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "build-gateway-release.sh",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "deploy-locked.sh",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "rollback-release.sh",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "verify-image-lock.sh",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "test-image-release.sh",
    ROOT / "output" / "pdf" / "techflow-image-version-lock-report.pdf",
    ROOT / "output" / "pdf" / "techflow-image-version-lock-presentation.pdf",
    ROOT / "output" / "presentation" / "techflow-image-version-lock.pptx",
]
OUTPUT = ROOT / "output" / "issue-18-artifact-manifest.json"
BINARY_SUFFIXES = {".pdf", ".pptx"}


def canonical_content(path: Path) -> tuple[bytes, str]:
    data = path.read_bytes()
    if path.suffix.lower() in BINARY_SUFFIXES:
        return data, "binary-raw"
    normalized = data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return normalized.encode("utf-8"), "text-lf-normalized"


def file_record(path: Path) -> dict[str, object]:
    content, mode = canonical_content(path)
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "size": len(content),
        "sha256": hashlib.sha256(content).hexdigest().upper(),
        "contentMode": mode,
    }


missing = [str(path) for path in FILES if not path.exists()]
if missing:
    raise FileNotFoundError(f"Missing artifacts: {missing}")

manifest = {
    "schemaVersion": "1.0",
    "issue": DATA["issue"],
    "title": DATA["title"],
    "status": DATA["status"],
    "generatedAt": DATA["validatedAt"],
    "hashPolicy": "binary raw bytes; UTF-8 text normalized to LF",
    "files": [file_record(path) for path in FILES],
}
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(OUTPUT)
