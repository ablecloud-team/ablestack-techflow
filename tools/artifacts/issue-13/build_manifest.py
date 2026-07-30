#!/usr/bin/env python3
"""Create a checksum manifest for Issue #13 deployment assets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = json.loads(
    (ROOT / "docs" / "decisions" / "activepieces-compose-deployment.json").read_text(
        encoding="utf-8"
    )
)
FILES = [
    ROOT / "docs" / "decisions" / "activepieces-compose-deployment.json",
    ROOT / "docs" / "reports" / "issue-13-activepieces-compose-deployment-validation.md",
    ROOT / "docs" / "runbooks" / "activepieces-compose-deployment.md",
    ROOT / "docs" / "environments" / "activepieces-test-server.md",
    ROOT / "deploy" / "compose" / "activepieces" / "compose.yml",
    ROOT / "deploy" / "compose" / "activepieces" / ".env.example",
    ROOT / "deploy" / "compose" / "activepieces" / "README.md",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "install-docker-ubuntu.sh",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "init-env.sh",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "deploy.sh",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "healthcheck.sh",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "status.sh",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "verify-persistence.sh",
    ROOT / "deploy" / "compose" / "activepieces" / "scripts" / "remove.sh",
    ROOT / "output" / "pdf" / "activepieces-compose-deployment-report.pdf",
    ROOT / "output" / "pdf" / "activepieces-compose-deployment-presentation.pdf",
    ROOT / "output" / "presentation" / "activepieces-compose-deployment.pptx",
]
OUTPUT = ROOT / "output" / "issue-13-artifact-manifest.json"


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
OUTPUT.write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print(OUTPUT)
