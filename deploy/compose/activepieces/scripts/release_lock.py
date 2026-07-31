#!/usr/bin/env python3
"""Validate, capture, and verify TechFlow immutable container releases."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import tempfile
from typing import Any


SERVICES = ("postgres", "redis", "app", "worker", "event-gateway", "ingress")
ENVIRONMENT_KEYS = {
    "postgres": "POSTGRES_IMAGE_REF",
    "redis": "REDIS_IMAGE_REF",
    "app": "AP_IMAGE_REF",
    "worker": "AP_IMAGE_REF",
    "event-gateway": "TECHFLOW_GATEWAY_IMAGE",
    "ingress": "CADDY_IMAGE_REF",
}
DIGEST_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")
SAFE_REF_PATTERN = re.compile(r"[a-zA-Z0-9._/:@-]{1,512}")


def run(command: list[str], *, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def load_lock(path: pathlib.Path, *, allow_pending: bool = False) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schemaVersion") != "1.0":
        raise ValueError("unsupported schemaVersion")
    release_id = data.get("releaseId", "")
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}", release_id):
        raise ValueError("invalid releaseId")
    if data.get("platform") != "linux/amd64":
        raise ValueError("platform must be linux/amd64")
    services = data.get("services")
    if not isinstance(services, dict) or set(services) != set(SERVICES):
        raise ValueError("release lock must contain exactly six services")
    for service in SERVICES:
        item = services[service]
        if item.get("environmentKey") != ENVIRONMENT_KEYS[service]:
            raise ValueError(f"invalid environmentKey for {service}")
        image_ref = item.get("imageRef", "")
        if not SAFE_REF_PATTERN.fullmatch(image_ref):
            raise ValueError(f"invalid imageRef for {service}")
        if service == "event-gateway":
            image_id = item.get("expectedImageId", "")
            if image_id == "PENDING_SERVER_BUILD" and allow_pending:
                continue
            if not DIGEST_PATTERN.fullmatch(image_id):
                raise ValueError("event-gateway expectedImageId must be an immutable sha256")
        else:
            digest = item.get("registryDigest", "")
            if not DIGEST_PATTERN.fullmatch(digest):
                raise ValueError(f"invalid registryDigest for {service}")
            if not image_ref.endswith("@" + digest):
                raise ValueError(f"imageRef digest mismatch for {service}")
            name_and_tag = image_ref.rsplit("@", 1)[0].rsplit("/", 1)[-1]
            if ":" not in name_and_tag:
                raise ValueError(f"version tag missing for {service}")
    return data


def atomic_json(path: pathlib.Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp_name, 0o640)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def write_env(data: dict[str, Any], output: pathlib.Path) -> None:
    values: dict[str, str] = {}
    for service in SERVICES:
        item = data["services"][service]
        key = item["environmentKey"]
        value = item["imageRef"]
        if key in values and values[key] != value:
            raise ValueError(f"conflicting imageRef for shared key {key}")
        values[key] = value
    gateway_version = data["services"]["event-gateway"].get("version", "runtime")
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}", gateway_version):
        gateway_version = "runtime"
    values["TECHFLOW_GATEWAY_VERSION"] = gateway_version
    output.parent.mkdir(parents=True, exist_ok=True)
    content = "".join(f"{key}={values[key]}\n" for key in sorted(values))
    fd, temp_name = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp_name, 0o640)
        os.replace(temp_name, output)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def inspect_service(service: str) -> dict[str, Any]:
    container = run(["docker", "compose", "--env-file", ".env", "ps", "-q", service]).stdout.strip()
    if not container:
        raise RuntimeError(f"missing container for {service}")
    inspected = run(["docker", "inspect", container])
    if inspected.returncode != 0:
        raise RuntimeError(f"container inspect failed for {service}")
    container_data = json.loads(inspected.stdout)[0]
    image_id = container_data["Image"]
    image = run(["docker", "image", "inspect", image_id])
    if image.returncode != 0:
        raise RuntimeError(f"image inspect failed for {service}")
    image_data = json.loads(image.stdout)[0]
    health = container_data.get("State", {}).get("Health", {}).get("Status", "none")
    return {
        "containerId": container_data["Id"],
        "configuredImage": container_data["Config"]["Image"],
        "imageId": image_id,
        "repoDigests": sorted(image_data.get("RepoDigests") or []),
        "health": health,
    }


def immutable_runtime_ref(configured: str, repo_digests: list[str], image_id: str) -> str:
    if "@sha256:" in configured:
        return configured
    digest = image_id
    if repo_digests:
        digest = repo_digests[0].rsplit("@", 1)[-1]
    base = configured.rsplit("@", 1)[0]
    if base.endswith(":latest"):
        base = base[:-7]
    return f"{base}@{digest}"


def capture(output: pathlib.Path, release_id: str) -> None:
    services: dict[str, Any] = {}
    for service in SERVICES:
        inspected = inspect_service(service)
        ref = immutable_runtime_ref(inspected["configuredImage"], inspected["repoDigests"], inspected["imageId"])
        item: dict[str, Any] = {
            "version": "runtime-capture",
            "environmentKey": ENVIRONMENT_KEYS[service],
            "imageRef": ref,
            "expectedImageId": inspected["imageId"],
            "configuredImage": inspected["configuredImage"],
            "healthAtCapture": inspected["health"],
        }
        if service != "event-gateway":
            item["registryDigest"] = ref.rsplit("@", 1)[-1]
        services[service] = item
    data = {
        "schemaVersion": "1.0",
        "releaseId": release_id,
        "createdAt": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "platform": "linux/amd64",
        "source": "runtime-capture",
        "services": services,
        "policy": {
            "requireTagAndDigest": True,
            "requirePreDeploymentBackup": True,
            "requireNoBuildRollback": True,
        },
    }
    atomic_json(output, data)


def verify_running(data: dict[str, Any]) -> None:
    failures: list[str] = []
    for service in SERVICES:
        expected = data["services"][service]
        actual = inspect_service(service)
        if actual["health"] != "healthy":
            failures.append(f"{service}:health")
        if service == "event-gateway":
            if actual["imageId"] != expected["expectedImageId"]:
                failures.append(f"{service}:image_id")
        else:
            digest = expected["registryDigest"]
            available = {item.rsplit("@", 1)[-1] for item in actual["repoDigests"]}
            available.add(actual["imageId"])
            if digest not in available:
                failures.append(f"{service}:digest")
    if failures:
        raise RuntimeError("release verification failed: " + ",".join(failures))
    print(f"release={data['releaseId']} services=6 digests=verified health=healthy")


def validate_source(data: dict[str, Any], compose_path: pathlib.Path, dockerfile_path: pathlib.Path) -> None:
    compose_text = compose_path.read_text(encoding="utf-8")
    for service in SERVICES:
        item = data["services"][service]
        if service != "event-gateway" and item["imageRef"] not in compose_text:
            raise ValueError(f"compose default does not match lock for {service}")
    gateway = data["services"]["event-gateway"]
    if gateway["imageRef"] not in compose_text:
        raise ValueError("compose default does not match gateway lock")
    dockerfile = dockerfile_path.read_text(encoding="utf-8")
    base_ref = gateway.get("baseImageRef", "")
    if base_ref and f"FROM {base_ref}" not in dockerfile:
        raise ValueError("gateway base image does not match lock")
    print(f"release={data['releaseId']} source_lock=valid services=6")


def compare(first: pathlib.Path, second: pathlib.Path) -> None:
    left = load_lock(first)
    right = load_lock(second)
    mismatches = []
    for service in SERVICES:
        if left["services"][service]["expectedImageId"] != right["services"][service]["expectedImageId"]:
            mismatches.append(service)
    if mismatches:
        raise RuntimeError("runtime image mismatch: " + ",".join(mismatches))
    print("runtime_images=identical services=6")


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--lock", required=True, type=pathlib.Path)
    validate_parser.add_argument("--compose", type=pathlib.Path)
    validate_parser.add_argument("--dockerfile", type=pathlib.Path)
    validate_parser.add_argument("--allow-pending", action="store_true")

    env_parser = subparsers.add_parser("env")
    env_parser.add_argument("--lock", required=True, type=pathlib.Path)
    env_parser.add_argument("--output", required=True, type=pathlib.Path)

    capture_parser = subparsers.add_parser("capture")
    capture_parser.add_argument("--output", required=True, type=pathlib.Path)
    capture_parser.add_argument("--release-id", required=True)

    verify_parser = subparsers.add_parser("verify-running")
    verify_parser.add_argument("--lock", required=True, type=pathlib.Path)

    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("--first", required=True, type=pathlib.Path)
    compare_parser.add_argument("--second", required=True, type=pathlib.Path)

    args = parser.parse_args()
    if args.command == "capture":
        capture(args.output, args.release_id)
        print(args.output)
        return 0
    if args.command == "compare":
        compare(args.first, args.second)
        return 0
    data = load_lock(args.lock, allow_pending=getattr(args, "allow_pending", False))
    if args.command == "env":
        write_env(data, args.output)
        print(args.output)
    elif args.command == "verify-running":
        verify_running(data)
    else:
        if bool(args.compose) != bool(args.dockerfile):
            raise ValueError("--compose and --dockerfile must be supplied together")
        if args.compose:
            validate_source(data, args.compose, args.dockerfile)
        else:
            print(f"release={data['releaseId']} lock=valid services=6")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
