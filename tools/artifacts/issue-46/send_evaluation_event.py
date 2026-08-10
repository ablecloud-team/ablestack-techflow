#!/usr/bin/env python3
"""Send a signed, D0-only Issue #46 evaluation event from Event Gateway."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import urllib.request
import uuid


def main() -> int:
    secret = os.environ.get("TECHFLOW_WEBHOOK_SECRET")
    if not secret:
        raise SystemExit("TECHFLOW_WEBHOOK_SECRET is required")
    event_id = f"issue46-evaluation-{uuid.uuid4()}"
    payload = {
        "eventId": event_id,
        "classification": "D0",
        "name": "Issue 46 Activepieces E2E",
        "sourceProfileIds": ["GENIE_MASTER"],
    }
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    timestamp = str(int(time.time()))
    digest = hmac.new(secret.encode("utf-8"), timestamp.encode("ascii") + b"." + body, hashlib.sha256).hexdigest()
    request = urllib.request.Request(
        "http://127.0.0.1:8081/techflow/hooks/rag/evaluation",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-TechFlow-Event-Id": event_id,
            "X-TechFlow-Timestamp": timestamp,
            "X-TechFlow-Signature": f"sha256={digest}",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        output = json.loads(response.read().decode("utf-8"))
    print(json.dumps({"httpStatus": response.status, **output}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
