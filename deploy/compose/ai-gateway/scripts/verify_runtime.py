#!/usr/bin/env python3
"""Issue #41 runtime canary using only the published local HTTP API."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from uuid import uuid4


def call(base_url: str, method: str, path: str, correlation: str, body: dict | None = None, key: str | None = None) -> tuple[int, dict]:
    headers = {"X-Correlation-Id": correlation}
    if key:
        headers["Idempotency-Key"] = key
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(base_url.rstrip("/") + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"canary request failed method={method} path={path} status={exc.code}") from exc


def expect(actual: int, expected: int, operation: str) -> None:
    if actual != expected:
        raise RuntimeError(f"{operation} expected={expected} actual={actual}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:18090")
    args = parser.parse_args()
    run = uuid4().hex[:8].upper()
    correlation = f"issue41-canary-{run.lower()}"
    profile = f"ISSUE41_CANARY_{run}"

    code, source_response = call(
        args.base_url,
        "POST",
        "/v1/sources",
        correlation,
        {
            "sourceProfileId": profile,
            "repository": "ablecloud-team/ablestack-cloud",
            "branch": "main",
            "commit": "c" * 40,
            "sourceKind": "SOURCE_CODE",
            "classification": "D0",
            "licenseSpdx": "Apache-2.0",
        },
        f"issue41-create-{run.lower()}",
    )
    expect(code, 201, "create-source")
    source = source_response["data"]

    code, approved_response = call(
        args.base_url,
        "POST",
        f"/v1/sources/{source['sourceId']}/approve",
        correlation,
        {"approvedBy": "issue41-canary"},
        f"issue41-approve-{run.lower()}",
    )
    expect(code, 200, "approve-source")
    approved = approved_response["data"]

    code, job_response = call(
        args.base_url,
        "POST",
        f"/v1/sources/{source['sourceId']}/ingestions",
        correlation,
        {"requestedBy": "issue41-canary"},
        f"issue41-ingest-{run.lower()}",
    )
    expect(code, 202, "create-ingestion")

    code, compatibility_response = call(
        args.base_url,
        "POST",
        "/v1/compatibility-sets",
        correlation,
        {
            "name": f"Issue 41 Canary {run}",
            "product": "ABLESTACK",
            "productVersion": run,
            "members": [{"sourceVersionId": approved["sourceVersionId"], "required": True}],
        },
        f"issue41-compat-{run.lower()}",
    )
    expect(code, 201, "create-compatibility-set")

    code, query_response = call(
        args.base_url,
        "POST",
        "/v1/rag/query",
        correlation,
        {
            "queryId": str(uuid4()),
            "question": "Issue 41 contract canary",
            "compatibilitySetId": compatibility_response["data"]["compatibilitySetId"],
            "classification": "D0",
        },
    )
    expect(code, 200, "query")
    if query_response["data"]["state"] != "ABSTAINED" or query_response["data"]["providerCalled"]:
        raise RuntimeError("Issue #41 query boundary must abstain without provider call")

    code, evaluation_response = call(
        args.base_url,
        "POST",
        "/v1/evaluations/runs",
        correlation,
        {
            "name": f"Issue 41 Canary {run}",
            "compatibilitySetId": compatibility_response["data"]["compatibilitySetId"],
            "providerProfileId": "OPENAI_RAG_DEFAULT_V1",
            "requestedBy": "issue41-canary",
        },
        f"issue41-eval-{run.lower()}",
    )
    expect(code, 202, "create-evaluation")

    code, deletion_response = call(
        args.base_url,
        "DELETE",
        f"/v1/sources/{source['sourceId']}",
        correlation,
        key=f"issue41-delete-{run.lower()}",
    )
    expect(code, 202, "withdraw-source")

    print(
        "runtime_canary=valid "
        f"profile={profile} sourceState=WITHDRAWN queryState=ABSTAINED "
        f"providerCalled=false ingestionJob={job_response['data']['jobId']} "
        f"evaluationRun={evaluation_response['data']['runId']} deletionJob={deletion_response['data']['jobId']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
