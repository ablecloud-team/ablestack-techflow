#!/usr/bin/env python3
"""Build a one-to-one inherited-element frame map for the 10-slide Issue #41 deck."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROLES = {
    1: "completion thesis",
    2: "verified result summary",
    3: "responsibility boundary",
    4: "database schema evidence",
    5: "api lifecycle",
    6: "implemented call path",
    7: "security and validation controls",
    8: "managed assets",
    9: "implementation sequence",
    10: "completion and next gate",
}


def main() -> int:
    inspect_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    records = [json.loads(line) for line in inspect_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    slides = []
    for slide_number in range(1, 11):
        shape_ids = [
            record["id"]
            for record in records
            if record.get("kind") == "textbox"
            and record.get("slide") == slide_number
            and not (
                record.get("text", "") == f"{slide_number:02d}"
                and record.get("bbox", [0, 0])[0] > 1100
            )
        ]
        targets: list[dict[str, object]] = [{"shapeIds": shape_ids, "action": "rewrite"}]
        for record in records:
            if record.get("kind") == "table" and record.get("slide") == slide_number:
                targets.append({"sourceElementId": record["id"], "action": "rewrite"})
        slides.append({
            "outputSlide": slide_number,
            "sourceSlide": slide_number,
            "narrativeRole": ROLES[slide_number],
            "reuseMode": "duplicate-slide",
            "editTargets": targets,
        })
    output_path.write_text(
        json.dumps({"outputSlides": slides, "omittedSourceSlides": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
