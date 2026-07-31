#!/usr/bin/env python3
"""Detect exact runtime secret values without printing those values."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

SECRET_KEYS = (
    "AP_API_KEY",
    "AP_ENCRYPTION_KEY",
    "AP_JWT_SECRET",
    "AP_POSTGRES_PASSWORD",
    "AP_REDIS_PASSWORD",
    "TECHFLOW_WEBHOOK_SECRET",
    "TECHFLOW_WEBHOOK_SECRET_PREVIOUS",
)


def load_secrets(path: Path) -> dict[str, bytes]:
    secrets: dict[str, bytes] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        if key in SECRET_KEYS and len(value) >= 8:
            secrets[key] = value.encode()
    return secrets


def scan_bytes(data: bytes, secrets: dict[str, bytes]) -> list[str]:
    return [name for name, value in secrets.items() if value in data]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--scan-root")
    parser.add_argument("--stdin-label")
    args = parser.parse_args()

    env_path = Path(args.env_file).resolve()
    secrets = load_secrets(env_path)
    findings: list[tuple[str, list[str]]] = []
    files_scanned = 0

    if args.scan_root:
        root = Path(args.scan_root).resolve()
        for path in root.rglob("*"):
            if not path.is_file() or path.resolve() == env_path:
                continue
            if "__pycache__" in path.parts:
                continue
            try:
                data = path.read_bytes()
            except OSError:
                continue
            files_scanned += 1
            matched = scan_bytes(data, secrets)
            if matched:
                findings.append((str(path.relative_to(root)), matched))

    if args.stdin_label:
        files_scanned += 1
        matched = scan_bytes(sys.stdin.buffer.read(), secrets)
        if matched:
            findings.append((args.stdin_label, matched))

    print(
        f"secrets_checked={len(secrets)} objects_scanned={files_scanned} "
        f"leaks={len(findings)}"
    )
    for label, names in findings:
        print(f"leak object={label} names={','.join(names)}")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
