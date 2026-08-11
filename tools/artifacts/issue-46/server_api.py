#!/usr/bin/env python3
"""Small no-secret client for the internal TechFlow AI Gateway API."""

from __future__ import annotations

import argparse
import json
import uuid
from urllib.error import HTTPError
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("method", choices=("GET", "POST", "DELETE"))
    parser.add_argument("path")
    parser.add_argument("--body", default=None)
    parser.add_argument("--base-url", default="http://techflow-ai-gateway:8090")
    parser.add_argument("--idempotency-key", default=None)
    args = parser.parse_args()
    data = args.body.encode("utf-8") if args.body is not None else None
    request = urllib.request.Request(args.base_url.rstrip("/") + args.path, data=data, method=args.method)
    request.add_header("Content-Type", "application/json")
    request.add_header("X-Correlation-Id", f"issue46-{uuid.uuid4()}")
    if args.idempotency_key:
        request.add_header("Idempotency-Key", args.idempotency_key)
    try:
        with urllib.request.urlopen(request, timeout=3600) as response:
            print(json.dumps(json.loads(response.read().decode("utf-8")), ensure_ascii=False))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP {exc.code}: {body[:1000]}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
