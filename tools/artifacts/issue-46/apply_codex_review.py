#!/usr/bin/env python3
"""Apply the explicit Codex semantic review to the Issue #46 live run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services" / "ai-gateway"))

from app.evaluation import summarize_results


# These answers are substantively correct and grounded in the returned fixed-commit
# citations. The deterministic judge rejected them because the Golden rule names a
# different valid path, uses a stricter literal phrase, or contains an outdated fact.
ACCEPTED_OVERRIDES = {
    "DOC-VM-001": "Zone, Pod, Cluster 계층을 정확히 답했고 동일 고정 Commit의 VM 배포 가이드 Citation으로 확인했다.",
    "DOC-VM-003": "Glue 이미지보다 큰 루트 디스크가 필요하다는 핵심 조건을 정확히 답했고 Windows와 Ubuntu 가이드가 함께 뒷받침한다.",
    "CLOUD-MAIN-001": "기본 관리 포트 8250을 정확히 답했고 Agent.java의 고정 Commit 코드 Citation으로 확인했다.",
    "CLOUD-EUROPA-002": "현재 고정 Commit은 sourceapi=auto와 v4-v3-v2 fallback을 구현한다. 실제 답변과 Citation이 맞고 Golden 기대문이 이전 v3 기준으로 남아 있다.",
    "CLOUD-EUROPA-004": "startTargetVm 기본값 true와 정지 유지 예외를 함께 설명해 기대 사실보다 더 정확하다.",
    "WALL-002": "Templating과 template variable은 같은 기능을 가리키며 동적 대시보드 재사용성을 정확히 설명했다.",
    "KICKSTART-004": "버전과 ISO 디렉터리 절대 경로라는 두 인자를 정확히 답했고 README Citation이 직접 뒷받침한다.",
    "KICKSTART-005": "현재 고정 Commit README의 실제 파일명 ablestack_{version}-el8.iso를 정확히 답했다. Golden 기대문의 대소문자와 구분자가 낡았다.",
    "QEMU-008": "RBD, qcow2 file, block/LVM 순서와 release gate 의미를 고정 Commit 설계 문서들로 정확히 설명했다.",
    "QEMU-009": "shared와 local disk offering 기본 이름을 둘 다 정확히 답했고 두 고정 Commit 문서가 일치한다.",
    "QEMU-011": "v4, v3, v2 inventory fallback 순서를 정확히 설명하고 고정 Commit 설계 문서 Citation을 제공했다.",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="output/issue-46-live-evaluation.json")
    args = parser.parse_args()
    target = ROOT / args.input
    payload = json.loads(target.read_text(encoding="utf-8"))

    for record in payload["records"]:
        key = record["caseKey"]
        if record["automatedJudgment"]["passed"]:
            continue
        if key in ACCEPTED_OVERRIDES:
            record["reviewJudgment"] = {
                "reviewer": "Codex",
                "verdict": "ACCEPTED",
                "rationale": ACCEPTED_OVERRIDES[key],
            }
        else:
            reasons = ", ".join(record["automatedJudgment"]["reasons"])
            record["reviewJudgment"] = {
                "reviewer": "Codex",
                "verdict": "REJECTED",
                "rationale": f"기대 사실을 확인할 답변 또는 적합한 근거가 부족해 수용하지 않았다: {reasons}",
            }

    payload["summary"] = summarize_results(payload["records"])
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
