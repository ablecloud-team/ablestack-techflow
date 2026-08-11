#!/usr/bin/env python3
"""Fail closed when a frozen runtime integration is changed indirectly."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


class GuardError(ValueError):
    pass


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(lock_path: Path, env_path: Path, compose_path: Path, ingress_path: Path) -> None:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    service = lock["services"]["github-chat-v1"]
    if service.get("state") != "FROZEN":
        raise GuardError("github-chat-v1 must remain FROZEN")
    if service.get("changePolicy") != "PRODUCT_OWNER_EXPLICIT_APPROVAL_ONLY":
        raise GuardError("github-chat-v1 change policy is not protected")

    manifest = lock_path.parent / service["flowManifest"]
    if sha256(manifest) != service["flowManifestSha256"]:
        raise GuardError("protected github-chat-v1 flow manifest changed")
    flow = json.loads(manifest.read_text(encoding="utf-8"))
    if flow.get("logicalId") != "github-chat-v1":
        raise GuardError("protected flow logical ID changed")
    if flow.get("runtime", {}).get("flowId") != service["flowId"]:
        raise GuardError("protected flow ID changed")
    if flow.get("runtime", {}).get("publishedVersionId") != service["publishedVersionId"]:
        raise GuardError("protected published flow version changed")
    expected_url = f"http://{service['chatAdapterHost']}:8081/internal/chat/github"
    if flow.get("action", {}).get("url") != expected_url:
        raise GuardError("protected Chat adapter URL changed")

    allowlist = set(load_env(env_path).get("AP_SSRF_ALLOW_LIST", "").split(","))
    missing = sorted(set(service["requiredSsrfAllowList"]) - allowlist)
    if missing:
        raise GuardError("protected Chat adapter is missing from AP_SSRF_ALLOW_LIST")

    compose = compose_path.read_text(encoding="utf-8")
    if f"ipv4_address: {service['chatAdapterIpv4']}" not in compose:
        raise GuardError("protected Chat adapter IPv4 changed")
    if f"- {service['chatAdapterHost']}" not in compose:
        raise GuardError("protected Chat adapter network alias changed")

    ingress = ingress_path.read_text(encoding="utf-8")
    if "/techflow/hooks/*" not in ingress or "reverse_proxy event-gateway:8081" not in ingress:
        raise GuardError("protected GitHub Webhook ingress changed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--compose", type=Path, required=True)
    parser.add_argument("--ingress", type=Path, required=True)
    args = parser.parse_args()
    validate(args.lock, args.env_file, args.compose, args.ingress)
    print("protected_service=github-chat-v1 state=frozen guard=passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
