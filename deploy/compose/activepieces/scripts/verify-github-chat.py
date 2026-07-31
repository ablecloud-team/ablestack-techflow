#!/usr/bin/env python3
"""Verify the GitHub ingress contract without printing secret material."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import urllib.error
import urllib.request
import uuid


def signature(secret: bytes, body: bytes) -> str:
    return "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()


def post(url: str, body: bytes, event: str, delivery: str, supplied: str) -> int:
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": event,
            "X-GitHub-Delivery": delivery,
            "X-Hub-Signature-256": supplied,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            response.read()
            return response.status
    except urllib.error.HTTPError as error:
        error.read()
        return error.code


def direct_webhook_status(base_url: str, flow_id: str) -> int:
    request = urllib.request.Request(
        f"{base_url}/api/v1/webhooks/{flow_id}",
        data=b"{}",
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            response.read()
            return response.status
    except urllib.error.HTTPError as error:
        error.read()
        return error.code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://172.16.0.231:8080")
    parser.add_argument("--flow-id", required=True)
    parser.add_argument("--organization", default="ablecloud-team")
    parser.add_argument("--repository", default="ablestack-techflow")
    parser.add_argument("--live-message", action="store_true")
    args = parser.parse_args()

    secret_text = os.environ.get("TECHFLOW_GITHUB_WEBHOOK_SECRET", "")
    if not secret_text:
        raise RuntimeError("TECHFLOW_GITHUB_WEBHOOK_SECRET is required")
    secret = secret_text.encode()
    endpoint = f"{args.base_url}/techflow/hooks/github/chat"
    repository_full_name = f"{args.organization}/{args.repository}"
    repository_url = f"https://github.com/{repository_full_name}"

    ping_body = json.dumps({"zen": "TechFlow verification"}, separators=(",", ":")).encode()
    ping_id = "verify-ping-" + uuid.uuid4().hex
    results = {
        "ping": post(endpoint, ping_body, "ping", ping_id, signature(secret, ping_body)),
        "invalid_signature": post(
            endpoint,
            ping_body,
            "ping",
            ping_id + "-invalid",
            "sha256=" + "0" * 64,
        ),
        "direct_activepieces": direct_webhook_status(args.base_url, args.flow_id),
    }

    ignored_payload = {
        "action": "closed",
        "number": 9999,
        "pull_request": {"merged": False},
        "repository": {
            "full_name": repository_full_name,
            "html_url": repository_url,
            "owner": {"login": args.organization},
        },
        "organization": {"login": args.organization},
        "sender": {"login": "techflow-verifier"},
    }
    ignored_body = json.dumps(ignored_payload, separators=(",", ":")).encode()
    ignored_id = "verify-unmerged-" + uuid.uuid4().hex
    results["unmerged_pr"] = post(
        endpoint,
        ignored_body,
        "pull_request",
        ignored_id,
        signature(secret, ignored_body),
    )

    if args.live_message:
        delivery = "verify-push-" + uuid.uuid4().hex
        payload = {
            "ref": "refs/heads/issue-19-verification",
            "before": "1" * 40,
            "after": "2" * 40,
            "created": False,
            "deleted": False,
            "forced": False,
            "compare": f"{repository_url}/compare/main...issue-19-verification",
            "commits": [{"id": "2" * 40}],
            "repository": {
                "full_name": repository_full_name,
                "html_url": repository_url,
                "owner": {"login": args.organization},
            },
            "organization": {"login": args.organization},
            "sender": {"login": "techflow-verifier"},
        }
        body = json.dumps(payload, separators=(",", ":")).encode()
        supplied = signature(secret, body)
        results["accepted"] = post(endpoint, body, "push", delivery, supplied)
        results["duplicate"] = post(endpoint, body, "push", delivery, supplied)

    expected = {
        "ping": 200,
        "invalid_signature": 401,
        "direct_activepieces": 404,
        "unmerged_pr": 200,
    }
    if args.live_message:
        expected.update({"accepted": 202, "duplicate": 200})
    passed = results == expected
    print(json.dumps({"passed": passed, "results": results}, sort_keys=True, separators=(",", ":")))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
