#!/usr/bin/env python3
"""Run a sanitized grounded-answer canary without printing question or answer text."""

from __future__ import annotations

import argparse
import json
from urllib.request import Request, urlopen
from uuid import uuid4


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:18090")
    parser.add_argument("--source-profile", default="GENIE_MASTER")
    parser.add_argument("--question", default="ABLESTACK Genie의 기술지원 역할을 근거와 함께 설명해줘")
    parser.add_argument("--expect-state", choices=("ANSWERED", "ABSTAINED", "FAILED"), default="ANSWERED")
    args = parser.parse_args()
    correlation_id = f"issue44-canary-{uuid4()}"
    payload = json.dumps(
        {
            "queryId": str(uuid4()),
            "question": args.question,
            "actorId": "issue44-runtime-canary",
            "sourceProfileIds": [args.source_profile],
            "classification": "D0",
            "locale": "ko-KR",
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = Request(
        f"{args.base_url.rstrip('/')}/v1/rag/query",
        data=payload,
        headers={"Content-Type": "application/json", "X-Correlation-Id": correlation_id},
        method="POST",
    )
    with urlopen(request, timeout=45) as response:
        result = json.loads(response.read())["data"]
    state = result["state"]
    citations = result.get("citations") or []
    if state != args.expect_state:
        raise RuntimeError(f"unexpected state: {state}")
    if state == "ANSWERED" and (not result.get("answer") or not citations):
        raise RuntimeError("grounded answer requires answer text and citations")
    if any(not item.get("commit") or not item.get("path") for item in citations):
        raise RuntimeError("citation lineage is incomplete")
    print(
        "issue44_canary=valid "
        f"state={state} profile={result.get('providerProfileId')} citations={len(citations)} "
        f"answerChars={len(result.get('answer') or '')} "
        f"retrievalProviderCalled={str(result.get('retrievalProviderCalled')).lower()} "
        f"generationProviderCalled={str(result.get('generationProviderCalled')).lower()} "
        f"errorCode={result.get('errorCode') or 'none'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
