#!/usr/bin/env python3
"""Issue #42 runtime canary without approving or activating a real source."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from uuid import uuid4


def call(
    base_url: str,
    method: str,
    path: str,
    correlation: str,
    body: dict | None = None,
    key: str | None = None,
) -> tuple[int, dict]:
    headers = {"X-Correlation-Id": correlation}
    if key:
        headers["Idempotency-Key"] = key
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(base_url.rstrip("/") + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def expect(actual: int, expected: int, operation: str) -> None:
    if actual != expected:
        raise RuntimeError(f"{operation} expected={expected} actual={actual}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:18090")
    args = parser.parse_args()
    run = uuid4().hex[:8].lower()
    correlation = f"issue42-canary-{run}"

    code, registry_response = call(args.base_url, "GET", "/v1/source-profiles", correlation)
    expect(code, 200, "list-source-profiles")
    profiles = registry_response["data"]
    if len(profiles) != 9 or {item["initialReviewer"] for item in profiles} != {"dhslove"}:
        raise RuntimeError("source registry must contain nine profiles assigned to dhslove")

    code, mirror_response = call(args.base_url, "GET", "/v1/source-mirrors", correlation)
    expect(code, 200, "list-source-mirrors")
    if len(mirror_response["data"]) != 7:
        raise RuntimeError("source mirror registry must contain seven repositories")

    code, candidate_response = call(
        args.base_url,
        "POST",
        "/v1/source-profiles/GENIE_MASTER/discoveries",
        correlation,
        {"detectedBy": "runtime-canary"},
        f"issue42-discover-genie-{run}",
    )
    expect(code, 201, "discover-genie")
    source = candidate_response["data"]
    if source["state"] == "REGISTERED":
        code, scan_response = call(
            args.base_url,
            "POST",
            f"/v1/source-versions/{source['sourceVersionId']}/scan",
            correlation,
            {"scannedBy": "source-fetcher"},
            f"issue42-scan-genie-{run}",
        )
        expect(code, 200, "scan-genie")
        source = scan_response["data"]
    if source["state"] != "QUARANTINED" or source["blockingViolationCount"] != 0:
        raise RuntimeError("GENIE canary must remain clean and quarantined pending reviewer approval")

    code, mirror_response = call(args.base_url, "GET", "/v1/source-mirrors", correlation)
    expect(code, 200, "list-source-mirrors-after-sync")
    genie_mirror = next(item for item in mirror_response["data"] if item["repository"].endswith("ablestack-genie"))
    if genie_mirror["state"] != "HEALTHY" or genie_mirror["lastHeadCommit"] != source["commit"]:
        raise RuntimeError("GENIE persistent mirror state must be healthy at the scanned commit")

    code, files_response = call(
        args.base_url, "GET", f"/v1/source-versions/{source['sourceVersionId']}/files", correlation
    )
    expect(code, 200, "list-source-files")
    files = files_response["data"]
    if len(files) != source["candidateFileCount"] or any("content" in item for item in files):
        raise RuntimeError("file inventory count or raw content boundary is invalid")

    code, denied_response = call(
        args.base_url,
        "POST",
        f"/v1/sources/{source['sourceId']}/ingestions",
        correlation,
        {"requestedBy": "activepieces"},
        f"issue42-denied-ingest-{run}",
    )
    expect(code, 409, "unapproved-ingestion")
    if denied_response.get("error", {}).get("code") != "INVALID_STATE":
        raise RuntimeError("unapproved source must fail closed")

    code, query_response = call(
        args.base_url,
        "POST",
        "/v1/rag/query",
        correlation,
        {"queryId": str(uuid4()), "question": "Issue 42 source boundary canary", "sourceProfileIds": ["GENIE_MASTER"]},
    )
    expect(code, 200, "query")
    if query_response["data"]["state"] != "ABSTAINED" or query_response["data"]["providerCalled"]:
        raise RuntimeError("Issue #42 query boundary must abstain without provider call")

    print(
        "runtime_canary=valid profiles=9 mirrors=7 reviewer=dhslove "
        f"sourceProfile=GENIE_MASTER sourceState={source['state']} files={len(files)} "
        "unapprovedIngestion=denied queryState=ABSTAINED providerCalled=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
