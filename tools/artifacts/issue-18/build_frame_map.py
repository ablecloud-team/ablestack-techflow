#!/usr/bin/env python3
"""Build the validated one-to-one Issue #18 template frame map."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROLES = [
    "immutable release outcome",
    "validated deployment and rollback result",
    "release responsibility flow",
    "locked image inventory",
    "upgrade and rollback runbook",
    "release evidence minimization flow",
    "thirteen verification controls",
    "implementation and documentation assets",
    "first business flow transition",
    "closing result",
]


def main() -> None:
    source = Path(sys.argv[1])
    output = Path(sys.argv[2])
    records = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line]
    slides = []
    for slide_number, role in enumerate(ROLES, start=1):
        targets = []
        for record in records:
            if record.get("slide") != slide_number:
                continue
            if record.get("kind") == "textbox":
                bbox = record.get("bbox") or [0, 0, 0, 0]
                if record.get("text", "").strip() == f"{slide_number:02d}" and bbox[0] > 1100 and bbox[1] > 600:
                    continue
                targets.append(record["id"])
            elif record.get("kind") in {"table", "chart"}:
                targets.append(record["id"])
        if not targets:
            raise RuntimeError(f"No editable inherited elements found on slide {slide_number}")
        slides.append({
            "outputSlide": slide_number,
            "sourceSlide": slide_number,
            "narrativeRole": role,
            "reuseMode": "duplicate-slide",
            "editTargets": [{"action": "rewrite", "sourceElementIds": targets}],
        })
    data = {"outputSlides": slides, "omittedSourceSlides": []}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
