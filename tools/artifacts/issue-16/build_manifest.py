#!/usr/bin/env python3
"""Create a checksum manifest for Issue #16 backup and recovery assets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = json.loads(
    (ROOT / "docs" / "decisions" / "techflow-state-backup-recovery.json").read_text(
        encoding="utf-8"
    )
)
FILES = [
    ROOT / "README.md",
    ROOT / "docs" / "adr" / "0002-techflow-secret-lifecycle.md",
    ROOT / "docs" / "adr" / "0003-techflow-state-backup-recovery.md",
    ROOT / "docs" / "decisions" / "techflow-state-backup-recovery.json",
    ROOT / "docs" / "reports" / "issue-16-backup-recovery-validation.md",
    ROOT / "docs" / "runbooks" / "secret-lifecycle.md",
    ROOT / "docs" / "runbooks" / "state-backup-recovery.md",
    ROOT / "docs" / "runbooks" / "activepieces-compose-deployment.md",
    ROOT / "docs" / "runbooks" / "https-webhook-ingress.md",
    ROOT / "docs" / "environments" / "activepieces-test-server.md",
    ROOT / "deploy" / "compose" / "activepieces" / "README.md",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "backup_manifest.py",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "backup-state.sh",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "restore-state-drill.sh",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "test-backup-recovery.sh",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "install-backup-timer.sh",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "verify-backup.sh",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "backup-secret-store.sh",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "restore-secret-store-drill.sh",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "test-secret-escrow.sh",
    ROOT / "deploy" / "compose" / "activepieces" / "systemd" / "techflow-state-backup.service",
    ROOT / "deploy" / "compose" / "activepieces" / "systemd" / "techflow-state-backup.timer",
    ROOT / "output" / "pdf" / "techflow-backup-recovery-report.pdf",
    ROOT / "output" / "pdf" / "techflow-backup-recovery-presentation.pdf",
    ROOT / "output" / "presentation" / "techflow-backup-recovery.pptx",
]
OUTPUT = ROOT / "output" / "issue-16-artifact-manifest.json"
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
