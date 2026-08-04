#!/usr/bin/env python3
"""Export the deterministic Issue #41 OpenAPI contract."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import Settings
from app.main import create_app
from app.store import MemoryStore


OUTPUT = ROOT / "openapi" / "techflow-ai-gateway-v1.json"


def main() -> int:
    schema = create_app(Settings(), MemoryStore()).openapi()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    operations = sum(
        1
        for path in schema["paths"].values()
        for method in path
        if method.lower() in {"get", "post", "delete", "put", "patch"}
    )
    print(f"openapi={OUTPUT} operations={operations}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
