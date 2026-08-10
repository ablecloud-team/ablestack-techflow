#!/usr/bin/env python3
"""Build checksums for the reviewed migration set."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "migrations"
OUTPUT = MIGRATIONS / "manifest.json"


def main() -> int:
    files = []
    for path in sorted(MIGRATIONS.glob("*.sql")):
        files.append(
            {
                "path": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "bytes": path.stat().st_size,
            }
        )
    data = {"schemaVersion": "2.0", "issue": 43, "files": files}
    OUTPUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"migration_manifest={OUTPUT} files={len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
