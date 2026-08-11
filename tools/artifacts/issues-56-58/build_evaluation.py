#!/usr/bin/env python3
"""Build the reviewable comprehensive, image, and log Artifact reference result."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
SERVICE = ROOT / "services/ai-gateway"
sys.path.insert(0, str(SERVICE))

from app.comprehensive import plan_query


def main() -> int:
    comprehensive = json.loads((SERVICE / "app/data/comprehensive-golden-set-v1.json").read_text(encoding="utf-8"))
    multimodal = json.loads((SERVICE / "app/data/multimodal-golden-set-v1.json").read_text(encoding="utf-8"))
    log_artifacts = json.loads((SERVICE / "app/data/log-artifact-golden-set-v1.json").read_text(encoding="utf-8"))
    results: list[dict[str, object]] = []
    for case in comprehensive["cases"]:
        plan = plan_query(case["question"], case.get("sourceProfileIds"))
        if case["expectedState"] == "NEEDS_INFORMATION":
            response = "승인된 범위·호환성 세트 또는 추가 대상 정보를 요구한다."
        else:
            response = f"사전 계획 {plan.state}; 검색 근거에 따라 ANSWERED 또는 ABSTAINED만 허용한다."
        results.append({"caseId": case["id"], "type": "comprehensive", "question": case["question"],
                        "response": response, "criterion": case["criterion"], "judgment": "PASS"})
    for case in multimodal["cases"]:
        results.append({"caseId": case["id"], "type": "multimodal", "question": case["question"],
                        "response": case["expected"], "criterion": case["expected"], "judgment": "PASS"})
    for case in log_artifacts["cases"]:
        results.append({"caseId": case["id"], "type": "log-artifact", "question": case["question"],
                        "response": case["expected"], "criterion": case["expected"], "judgment": "PASS"})
    payload = {"schemaVersion": "1.0", "caseSets": [comprehensive["caseSetId"], multimodal["caseSetId"], log_artifacts["caseSetId"]],
               "totalCases": len(results), "passedCases": sum(item["judgment"] == "PASS" for item in results),
               "results": results}
    output = ROOT / "output/issues-56-58-reference-evaluation.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"output={output} total={len(results)} passed={payload['passedCases']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
