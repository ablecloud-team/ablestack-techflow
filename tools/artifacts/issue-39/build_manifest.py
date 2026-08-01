#!/usr/bin/env python3
"""Create the checksum manifest for Issue #39 security and data policy assets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
POLICY = json.loads(
    (ROOT / "docs" / "decisions" / "techflow-security-data-policy.json").read_text(
        encoding="utf-8"
    )
)
FILES = [
    ROOT / "README.md",
    ROOT / "docs" / "plans" / "techflow-product-roadmap.md",
    ROOT / "docs" / "adr" / "0006-techflow-security-threat-model.md",
    ROOT / "docs" / "adr" / "0007-techflow-data-classification-retention.md",
    ROOT / "docs" / "decisions" / "techflow-security-data-policy.json",
    ROOT / "docs" / "runbooks" / "security-data-governance.md",
    ROOT / "docs" / "reports" / "issue-39-security-data-policy-validation.md",
    ROOT / "tools" / "policy" / "validate_security_data_policy.py",
    ROOT / "tools" / "policy" / "test_validate_security_data_policy.py",
    ROOT / "tools" / "artifacts" / "issue-39" / "build_manifest.py",
    ROOT / "tools" / "artifacts" / "issue-39" / "validate_artifacts.py",
    ROOT / "output" / "pdf" / "techflow-security-data-policy-report.pdf",
    ROOT / "output" / "pdf" / "techflow-security-data-policy-presentation.pdf",
    ROOT / "output" / "presentation" / "techflow-security-data-policy.pptx",
]
OUTPUT = ROOT / "output" / "issue-39-artifact-manifest.json"
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
    "issue": POLICY["issue"],
    "title": POLICY["title"],
    "status": "completed",
    "generatedAt": f"{POLICY['decisionDate']}T08:00:00Z",
    "hashPolicy": "binary raw bytes; UTF-8 text normalized to LF",
    "files": [file_record(path) for path in FILES],
}
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(OUTPUT)
