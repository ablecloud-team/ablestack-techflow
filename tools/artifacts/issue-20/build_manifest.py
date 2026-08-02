#!/usr/bin/env python3
"""Create the checksum manifest for Issue #20 RAG PoC design assets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = json.loads((ROOT / "docs/decisions/techflow-rag-poc-contract.json").read_text(encoding="utf-8"))
FILES = [
    ROOT / "README.md",
    ROOT / "docs/plans/techflow-product-roadmap.md",
    ROOT / "docs/adr/0008-techflow-rag-poc-architecture.md",
    ROOT / "docs/plans/issue-20-rag-poc-design.md",
    ROOT / "docs/decisions/techflow-rag-poc-contract.json",
    ROOT / "docs/runbooks/rag-poc-development.md",
    ROOT / "docs/reports/issue-20-rag-poc-design-review.md",
    ROOT / "tools/rag/validate_rag_poc_contract.py",
    ROOT / "tools/rag/test_validate_rag_poc_contract.py",
    ROOT / "tools/artifacts/issue-20/build_manifest.py",
    ROOT / "tools/artifacts/issue-20/validate_artifacts.py",
    ROOT / "output/pdf/techflow-rag-poc-design-report.pdf",
    ROOT / "output/pdf/techflow-rag-poc-design-presentation.pdf",
    ROOT / "output/presentation/techflow-rag-poc-design.pptx",
]
BINARY_SUFFIXES = {".pdf", ".pptx"}


def canonical(path: Path) -> tuple[bytes, str]:
    data = path.read_bytes()
    if path.suffix.lower() in BINARY_SUFFIXES:
        return data, "binary-raw"
    text = data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return text.encode("utf-8"), "text-lf-normalized"


def record(path: Path) -> dict[str, object]:
    content, mode = canonical(path)
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
    "issue": CONTRACT["issue"],
    "title": CONTRACT["title"],
    "status": "design-completed-approval-pending",
    "generatedAt": f"{CONTRACT['decisionDate']}T09:00:00Z",
    "hashPolicy": "binary raw bytes; UTF-8 text normalized to LF",
    "files": [record(path) for path in FILES],
}
OUTPUT = ROOT / "output/issue-20-design-artifact-manifest.json"
OUTPUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(OUTPUT)
