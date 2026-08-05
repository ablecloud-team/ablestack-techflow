#!/usr/bin/env python3
"""Run the approved Issue #43 ingestion and retrieval canary without secrets."""

from __future__ import annotations

import argparse
import json
from uuid import uuid4
import urllib.request


def request(url: str, method: str, path: str, body: dict | None = None, *, idempotency: str | None = None) -> dict:
    headers = {"X-Correlation-Id": f"issue43-canary-{uuid4()}"}
    if idempotency:
        headers["Idempotency-Key"] = idempotency
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    with urllib.request.urlopen(urllib.request.Request(url + path, data=data, headers=headers, method=method), timeout=180) as response:
        return json.load(response)["data"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:18090")
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--profile", default="GENIE_MASTER")
    parser.add_argument("--question", default="ABLESTACK Genie 설치와 구성 검증 절차는 무엇인가?")
    args = parser.parse_args()
    run_key = uuid4().hex
    job = request(args.url, "POST", f"/v1/sources/{args.source_id}/ingestions",
                  {"requestedBy": "issue43-canary"}, idempotency=f"issue43-ingest-{run_key}")
    completed = request(args.url, "POST", f"/v1/jobs/{job['jobId']}/run",
                        {"requestedBy": "issue43-canary", "providerProfileId": "OPENAI_EMBEDDING_V1"},
                        idempotency=f"issue43-run-{run_key}")
    retrieval = request(args.url, "POST", "/v1/rag/retrieve",
                        {"queryId": str(uuid4()), "question": args.question,
                         "sourceProfileIds": [args.profile], "classification": "D0"})
    output = {
        "jobState": completed["state"], "metrics": completed.get("metrics", {}),
        "resultCount": retrieval["resultCount"], "provider": retrieval["provider"],
        "providerCalled": retrieval["providerCalled"],
        "citations": [{key: item.get(key) for key in ("repository", "branch", "commit", "path", "startLine", "endLine", "symbol")}
                      for item in retrieval["results"][:3]],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))
    if completed["state"] != "SUCCEEDED" or retrieval["resultCount"] < 1:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
