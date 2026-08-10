#!/usr/bin/env python3
"""Atomically reindex the nine active Issue #46 sources through AI Gateway."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
import uuid


BASE_URL = "http://techflow-ai-gateway:8090"
SOURCES = [
    ("GENIE_MASTER", "42000000-0000-0000-0000-000000000007"),
    ("KICKSTART_MASTER", "42000000-0000-0000-0000-000000000008"),
    ("SHARED_DOCS", "42000000-0000-0000-0000-000000000001"),
    ("COCKPIT_DIPLO", "42000000-0000-0000-0000-000000000006"),
    ("QEMU_EXEC_TOOLS_MAIN", "42000000-0000-0000-0000-000000000009"),
    ("WALL_MAIN", "42000000-0000-0000-0000-000000000005"),
    ("CLOUD_MAIN", "42000000-0000-0000-0000-000000000002"),
    ("CLOUD_EUROPA", "42000000-0000-0000-0000-000000000004"),
    ("CLOUD_DIPLO", "42000000-0000-0000-0000-000000000003"),
]


def api(method: str, path: str, body: dict, idempotency_key: str) -> dict:
    request = urllib.request.Request(
        BASE_URL + path,
        data=json.dumps(body, separators=(",", ":")).encode("utf-8"),
        method=method,
        headers={
            "Content-Type": "application/json",
            "X-Correlation-Id": f"issue46-openai-reindex-{uuid.uuid4()}",
            "Idempotency-Key": idempotency_key,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=7200) as response:
            return json.loads(response.read().decode("utf-8"))["data"]
    except urllib.error.HTTPError as exc:
        safe = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"{method} {path} returned HTTP {exc.code}: {safe}") from None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-at", choices=[profile for profile, _ in SOURCES])
    parser.add_argument("--key-suffix", default="v1")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    completed = []
    selected = SOURCES
    if args.start_at:
        selected = SOURCES[[profile for profile, _ in SOURCES].index(args.start_at):]
    for index, (profile, source_id) in enumerate(selected, 1):
        key = profile.lower().replace("_", "-")
        job = api(
            "POST",
            f"/v1/sources/{source_id}/ingestions",
            {"requestedBy": "dhslove"},
            f"issue46-openai-reindex-create-{key}-{args.key_suffix}",
        )
        if job["jobType"] != "REINDEX":
            raise RuntimeError(f"{profile} did not create a REINDEX job")
        result = api(
            "POST",
            f"/v1/jobs/{job['jobId']}/run",
            {"requestedBy": "dhslove"},
            f"issue46-openai-reindex-run-{key}-{args.key_suffix}",
        )
        if result["state"] != "SUCCEEDED":
            raise RuntimeError(f"{profile} reindex did not succeed")
        record = {"sequence": index, "sourceProfileId": profile, "jobId": result["jobId"], "metrics": result["metrics"]}
        completed.append(record)
        print(json.dumps(record, ensure_ascii=False), flush=True)
    print(json.dumps({"state": "SUCCEEDED", "sources": completed}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"state": "FAILED", "errorType": type(exc).__name__}, ensure_ascii=False), file=sys.stderr)
        raise
