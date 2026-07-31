#!/usr/bin/env python3
"""Create the checksum manifest for Issue #19 GitHub Chat automation assets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DATA = json.loads(
    (ROOT / "docs" / "decisions" / "github-chat-webhook-contract.json").read_text(
        encoding="utf-8"
    )
)
FILES = [
    ROOT / "README.md",
    ROOT / "docs" / "plans" / "issue-19-github-chat-webhook-design.md",
    ROOT / "docs" / "decisions" / "github-chat-webhook-contract.json",
    ROOT / "docs" / "runbooks" / "github-chat-webhook.md",
    ROOT / "docs" / "reports" / "issue-19-github-chat-webhook-validation.md",
    ROOT / "deploy" / "compose" / "activepieces" / ".env.example",
    ROOT / "deploy" / "compose" / "activepieces" / "README.md",
    ROOT / "deploy" / "compose" / "activepieces" / "compose.yml",
    ROOT / "deploy" / "compose" / "activepieces" / "image-lock.json",
    ROOT / "deploy" / "compose" / "activepieces" / "event-gateway" / "Dockerfile",
    ROOT / "deploy" / "compose" / "activepieces" / "event-gateway" / "gateway.py",
    ROOT / "deploy" / "compose" / "activepieces" / "event-gateway" / "test_gateway.py",
    ROOT / "deploy" / "compose" / "activepieces" / "ingress" / "Caddyfile",
    ROOT / "deploy" / "compose" / "activepieces" / "flows" / "github-chat-v1.json",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "configure-ingress.sh",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "deploy-locked.sh",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "init-env.sh",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "secret_scan.py",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "secretctl.sh",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "verify-github-chat.py",
    ROOT / "output" / "pdf" / "github-chat-webhook-report.pdf",
    ROOT / "output" / "pdf" / "github-chat-webhook-presentation.pdf",
    ROOT / "output" / "presentation" / "github-chat-webhook.pptx",
]
OUTPUT = ROOT / "output" / "issue-19-artifact-manifest.json"
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
    "status": "completed",
    "generatedAt": f"{DATA['decisionDate']}T14:50:00Z",
    "hashPolicy": "binary raw bytes; UTF-8 text normalized to LF",
    "files": [file_record(path) for path in FILES],
}
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(OUTPUT)
