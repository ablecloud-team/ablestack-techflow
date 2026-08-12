from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "output/issue-22-artifact-manifest.json"
FILES = [
    "docs/plans/issue-22-chat-community-approval-design.md",
    "docs/runbooks/chat-community-approval.md",
    "docs/reports/issue-22-chat-community-approval-validation.md",
    "services/ai-gateway/app/chat_assist.py",
    "services/ai-gateway/migrations/0009_chat_approval_up.sql",
    "services/ai-gateway/openapi/techflow-ai-gateway-v1.json",
    "output/presentation/techflow-chat-community-approval.pptx",
    "output/pdf/techflow-chat-community-approval-presentation.pdf",
    "output/pdf/techflow-chat-community-approval-report.pdf",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    missing = [item for item in FILES if not (ROOT / item).is_file()]
    if missing:
        raise RuntimeError(f"missing artifacts: {missing}")
    payload = {
        "schemaVersion": "1.0",
        "issue": 22,
        "scope": "chat-community-approval",
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
