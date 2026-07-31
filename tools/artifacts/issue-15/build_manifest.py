#!/usr/bin/env python3
"""Create a checksum manifest for Issue #15 secret lifecycle assets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = json.loads(
    (ROOT / "docs" / "decisions" / "techflow-secret-management.json").read_text(
        encoding="utf-8"
    )
)
FILES = [
    ROOT / "README.md",
    ROOT / "docs" / "adr" / "0002-techflow-secret-lifecycle.md",
    ROOT / "docs" / "decisions" / "techflow-secret-management.json",
    ROOT / "docs" / "reports" / "issue-15-secret-management-validation.md",
    ROOT / "docs" / "runbooks" / "secret-lifecycle.md",
    ROOT / "docs" / "runbooks" / "activepieces-compose-deployment.md",
    ROOT / "docs" / "runbooks" / "https-webhook-ingress.md",
    ROOT / "docs" / "environments" / "activepieces-test-server.md",
    ROOT / "deploy" / "compose" / "activepieces" / ".env.example",
    ROOT / "deploy" / "compose" / "activepieces" / "README.md",
    ROOT / "deploy" / "compose" / "activepieces" / "event-gateway" / "gateway.py",
    ROOT / "deploy" / "compose" / "activepieces" / "event-gateway" / "test_gateway.py",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "init-env.sh",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "configure-ingress.sh",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "deploy.sh",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "verify-webhook.sh",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "secret_env.py",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "secret_scan.py",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "secretctl.sh",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "verify-secrets.sh",
    ROOT / "output" / "pdf" / "techflow-secret-management-report.pdf",
    ROOT / "output" / "pdf" / "techflow-secret-management-presentation.pdf",
    ROOT / "output" / "presentation" / "techflow-secret-management.pptx",
]
OUTPUT = ROOT / "output" / "issue-15-artifact-manifest.json"


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
    "title": DATA["title"],
    "status": DATA["status"],
    "generatedAt": DATA["validatedAt"],
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
OUTPUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(OUTPUT)
