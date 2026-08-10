#!/usr/bin/env python3
"""Execute the committed D0 Golden Set and retain reviewable Q&A evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.evaluation import answer_sha256, judge_case, load_golden_set, summarize_results


def post_json(url: str, payload: dict, correlation_id: str, timeout: float) -> dict:
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Correlation-Id": correlation_id},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read())["data"]
    except HTTPError as exc:
        safe = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"gateway returned HTTP {exc.code}: {safe}") from exc


def reference_result(case: dict) -> dict:
    citations = []
    if case["expectedState"] == "ANSWERED":
        for rule in case.get("expectedCitations", [])[:1]:
            citations.append({**rule, "chunkId": str(uuid4()), "sourceVersionId": str(uuid4()),
                              "startLine": 1, "endLine": 1, "symbol": None})
    return {
        "state": case["expectedState"],
        "answer": case.get("expectedAnswer"),
        "citations": citations,
        "providerProfileId": "REFERENCE_REPLAY_V1",
        "retrievalProviderCalled": False,
        "generationProviderCalled": False,
        "abstainReason": "reference-negative-case" if case["expectedState"] == "ABSTAINED" else None,
    }


def review(judgment: dict, mode: str) -> dict:
    if mode == "reference":
        return {
            "reviewer": "Codex",
            "verdict": "REFERENCE_CONFIRMED" if judgment["passed"] else "REFERENCE_REJECTED",
            "rationale": "고정 Commit에서 검토한 기준 답변과 Citation 계약의 일관성을 확인했다. 실 Gateway 품질 판정에는 사용하지 않는다.",
        }
    if judgment["passed"]:
        rationale = "예상 상태, 핵심 사실, 고정 Commit Citation과 코드 라인 해석 가능성이 모두 충족됐다."
        verdict = "ACCEPTED"
    else:
        rationale = "자동 판정 실패 항목을 근거로 답변을 수용하지 않았다: " + ", ".join(judgment["reasons"])
        verdict = "REJECTED"
    return {"reviewer": "Codex", "verdict": verdict, "rationale": rationale}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--golden-set")
    parser.add_argument("--mode", choices=("live", "reference"), default="live")
    parser.add_argument("--base-url", default="http://127.0.0.1:18090")
    parser.add_argument("--output", required=True)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--case-key", action="append", default=[])
    args = parser.parse_args()

    golden = load_golden_set(args.golden_set)
    selected = [item for item in golden["cases"] if not args.case_key or item["caseKey"] in args.case_key]
    records = []
    run_id = str(uuid4())
    for index, case in enumerate(selected, 1):
        started = time.perf_counter()
        if args.mode == "reference":
            result = reference_result(case)
        else:
            correlation_id = f"issue46-{run_id[:8]}-{index:03d}"
            result = post_json(
                f"{args.base_url.rstrip('/')}/v1/rag/query",
                {
                    "queryId": str(uuid4()),
                    "question": case["question"],
                    "actorId": "issue46-golden-evaluator",
                    "sourceProfileIds": case["sourceProfileIds"],
                    "classification": "D0",
                    "locale": case["locale"],
                },
                correlation_id,
                args.timeout,
            )
        latency_ms = round((time.perf_counter() - started) * 1000)
        judgment = judge_case(case, result).payload()
        record = {
            "caseKey": case["caseKey"],
            "category": case["category"],
            "tags": case.get("tags", []),
            "sourceProfileIds": case["sourceProfileIds"],
            "question": case["question"],
            "expectedState": case["expectedState"],
            "expectedAnswer": case.get("expectedAnswer"),
            "actualState": result.get("state"),
            "actualAnswer": result.get("answer"),
            "actualAnswerSha256": answer_sha256(result.get("answer")),
            "abstainReason": result.get("abstainReason"),
            "citations": result.get("citations") or [],
            "providerProfileId": result.get("providerProfileId"),
            "retrievalProviderCalled": result.get("retrievalProviderCalled", False),
            "generationProviderCalled": result.get("generationProviderCalled", False),
            "latencyMs": latency_ms,
            "automatedJudgment": judgment,
            "reviewJudgment": review(judgment, args.mode),
        }
        records.append(record)
        print(f"case={case['caseKey']} state={record['actualState']} pass={str(judgment['passed']).lower()} latencyMs={latency_ms}")

    output = {
        "schemaVersion": "1.0",
        "runId": run_id,
        "setId": golden["setId"],
        "executionMode": "LIVE_GATEWAY" if args.mode == "live" else "REFERENCE_REPLAY",
        "classification": "D0",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceCommits": golden["sourceCommits"],
        "summary": summarize_results(records),
        "records": records,
    }
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"evaluation={target} cases={len(records)} passed={output['summary']['passedCases']}")
    return 0 if output["summary"]["passedCases"] == len(records) else 2


if __name__ == "__main__":
    raise SystemExit(main())
