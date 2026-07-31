#!/usr/bin/env python3
"""Create and inspect non-secret TechFlow state-backup manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create(args: argparse.Namespace) -> None:
    directory = Path(args.directory)
    files = {}
    for name in ("postgres.dump", "redis.rdb"):
        path = directory / name
        if not path.is_file():
            raise FileNotFoundError(path)
        files[name] = {
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }

    manifest = {
        "schemaVersion": "1.0",
        "createdAt": args.created_at,
        "completedAt": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "label": args.label,
        "source": {
            "composeProject": "techflow-activepieces",
            "postgresImage": args.postgres_image,
            "redisImage": args.redis_image,
        },
        "postgres": {
            "database": args.database,
            "publicTableCount": args.table_count,
            "databaseBytes": args.database_bytes,
            "probeId": args.probe_id or None,
        },
        "redis": {
            "database": 0,
            "sourceObservedKeyCount": args.redis_key_count,
            "probeId": args.probe_id or None,
        },
        "files": files,
        "security": {
            "containsRuntimeSecrets": False,
            "excluded": [
                ".env",
                "/etc/ablestack-techflow/secrets",
                "secret-audit.jsonl",
            ],
        },
    }
    (directory / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def read_field(args: argparse.Namespace) -> None:
    value: object = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    for part in args.field.split("."):
        if not isinstance(value, dict) or part not in value:
            raise KeyError(args.field)
        value = value[part]
    if value is None:
        return
    if isinstance(value, (dict, list)):
        print(json.dumps(value, ensure_ascii=False))
    else:
        print(value)


def verify(args: argparse.Namespace) -> None:
    directory = Path(args.directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("security", {}).get("containsRuntimeSecrets") is not False:
        raise ValueError("Manifest does not explicitly exclude runtime secrets.")
    for name, record in manifest["files"].items():
        path = directory / name
        if not path.is_file():
            raise FileNotFoundError(path)
        if path.stat().st_size != record["bytes"]:
            raise ValueError(f"Size mismatch: {name}")
        if sha256(path) != record["sha256"]:
            raise ValueError(f"Checksum mismatch: {name}")
    print("manifest=valid payload_checksums=valid secrets=excluded")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    commands = root.add_subparsers(dest="command", required=True)

    create_parser = commands.add_parser("create")
    create_parser.add_argument("--directory", required=True)
    create_parser.add_argument("--created-at", required=True)
    create_parser.add_argument("--label", required=True)
    create_parser.add_argument("--postgres-image", required=True)
    create_parser.add_argument("--redis-image", required=True)
    create_parser.add_argument("--database", required=True)
    create_parser.add_argument("--database-bytes", required=True, type=int)
    create_parser.add_argument("--table-count", required=True, type=int)
    create_parser.add_argument("--redis-key-count", required=True, type=int)
    create_parser.add_argument("--probe-id", default="")
    create_parser.set_defaults(func=create)

    read_parser = commands.add_parser("read")
    read_parser.add_argument("--manifest", required=True)
    read_parser.add_argument("--field", required=True)
    read_parser.set_defaults(func=read_field)

    verify_parser = commands.add_parser("verify")
    verify_parser.add_argument("--directory", required=True)
    verify_parser.set_defaults(func=verify)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        args.func(args)
    except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError) as error:
        print(f"backup manifest error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
