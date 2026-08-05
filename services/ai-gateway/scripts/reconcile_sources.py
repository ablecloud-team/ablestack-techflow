#!/usr/bin/env python3
"""Reconcile all immutable source profiles through the internal gateway."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.source_registry import SOURCE_PROFILES


def _log(event: str, **fields: object) -> None:
    print(json.dumps({"event": event, **fields}, ensure_ascii=True, separators=(",", ":")), flush=True)


def _window(interval: int) -> int:
    return int(datetime.now(timezone.utc).timestamp()) // interval


def reconcile_once(base_url: str, interval: int) -> int:
    failures = 0
    window = _window(interval)
    for profile_id in SOURCE_PROFILES:
        body = json.dumps({"detectedBy": "source-reconciler"}).encode("utf-8")
        request = urllib.request.Request(
            f"{base_url.rstrip('/')}/v1/source-profiles/{profile_id}/discoveries",
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Correlation-Id": f"source-reconcile-{window}-{profile_id.lower()}",
                "Idempotency-Key": f"source-reconcile-{window}-{profile_id.lower()}",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=310) as response:
                if response.status != 201:
                    raise RuntimeError(f"unexpected status {response.status}")
            _log("source_reconcile_succeeded", sourceProfileId=profile_id, window=window)
        except (urllib.error.URLError, RuntimeError) as exc:
            failures += 1
            _log("source_reconcile_failed", sourceProfileId=profile_id, errorType=type(exc).__name__, window=window)
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    base_url = os.getenv("TECHFLOW_GATEWAY_URL", "http://gateway:8090")
    interval = int(os.getenv("TECHFLOW_SOURCE_RECONCILE_INTERVAL_SECONDS", "21600"))
    if interval < 3600:
        raise SystemExit("reconciliation interval must be at least 3600 seconds")
    while True:
        failures = reconcile_once(base_url, interval)
        if args.once:
            return 1 if failures else 0
        _log("source_reconcile_cycle_completed", failures=failures, nextRunSeconds=interval)
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
