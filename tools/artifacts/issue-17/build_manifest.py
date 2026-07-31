#!/usr/bin/env python3
"""Create a checksum manifest for Issue #17 observability assets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = json.loads((ROOT / "docs" / "decisions" / "techflow-observability.json").read_text(encoding="utf-8"))
FILES = [
    ROOT / "README.md",
    ROOT / "docs" / "adr" / "0004-techflow-observability.md",
    ROOT / "docs" / "decisions" / "techflow-observability.json",
    ROOT / "docs" / "reports" / "issue-17-observability-validation.md",
    ROOT / "docs" / "runbooks" / "observability.md",
    ROOT / "deploy" / "compose" / "activepieces" / "compose.yml",
    ROOT / "deploy" / "compose" / "activepieces" / "observability" / "observer.py",
    ROOT / "deploy" / "compose" / "activepieces" / "observability" / "test_observer.py",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "install-observability.sh",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "verify-observability.sh",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "test-observability.sh",
    ROOT / "deploy" / "compose" / "activepieces" / "systemd" / "techflow-observer.service",
    ROOT / "deploy" / "compose" / "activepieces" / "systemd" / "techflow-observer.timer",
    ROOT / "deploy" / "compose" / "activepieces" / "systemd" / "techflow-observer-notify@.service",
    ROOT / "output" / "pdf" / "techflow-observability-report.pdf",
    ROOT / "output" / "pdf" / "techflow-observability-presentation.pdf",
    ROOT / "output" / "presentation" / "techflow-observability.pptx",
]
OUTPUT = ROOT / "output" / "issue-17-artifact-manifest.json"
BINARY_SUFFIXES = {".pdf", ".pptx"}


def canonical_content(path: Path) -> tuple[bytes, str]:
    data = path.read_bytes()
    if path.suffix.lower() in BINARY_SUFFIXES:
        return data, "binary-raw"
    normalized = data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return normalized.encode("utf-8"), "text-lf-normalized"


def file_record(path: Path) -> dict[str, object]:
    content, content_mode = canonical_content(path)
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "size": len(content),
        "sha256": hashlib.sha256(content).hexdigest().upper(),
        "contentMode": content_mode,
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
