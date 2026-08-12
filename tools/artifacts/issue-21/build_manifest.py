from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "output/issue-21-artifact-manifest.json"
FILES = [
    "docs/plans/issue-21-community-assist-design.md",
    "docs/runbooks/community-assist.md",
    "docs/reports/issue-21-community-assist-validation.md",
    "deploy/compose/activepieces/flows/community-assist-v1.json",
    "services/ai-gateway/openapi/techflow-ai-gateway-v1.json",
    "output/presentation/techflow-community-assist.pptx",
    "output/pdf/techflow-community-assist-presentation.pdf",
    "output/pdf/techflow-community-assist-report.pdf",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    missing = [item for item in FILES if not (ROOT / item).is_file()]
    if missing:
        raise RuntimeError(f"missing artifacts: {missing}")
    payload = {
        "schemaVersion": "1.0",
        "issue": 21,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "artifacts": [
            {"path": item, "bytes": (ROOT / item).stat().st_size, "sha256": sha256(ROOT / item)}
            for item in FILES
        ],
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"manifest={OUTPUT} artifacts={len(FILES)}")


if __name__ == "__main__":
    main()
