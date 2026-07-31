#!/usr/bin/env python3
"""Read and atomically update a runtime env file without secret values in argv."""

from __future__ import annotations

import argparse
import os
import stat
import sys
import tempfile
from pathlib import Path


def parse_env(path: Path) -> list[tuple[str | None, str]]:
    records: list[tuple[str | None, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            records.append((None, line))
            continue
        key, value = line.split("=", 1)
        records.append((key, value))
    return records


def atomic_set(path: Path, key: str, value: str) -> None:
    records = parse_env(path)
    found = False
    output: list[str] = []
    for current_key, current_value in records:
        if current_key == key:
            output.append(f"{key}={value}")
            found = True
        elif current_key is None:
            output.append(current_value)
        else:
            output.append(f"{current_key}={current_value}")
    if not found:
        output.append(f"{key}={value}")

    file_stat = path.stat()
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write("\n".join(output) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, stat.S_IMODE(file_stat.st_mode))
        if hasattr(os, "chown"):
            os.chown(temporary, file_stat.st_uid, file_stat.st_gid)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def inventory(path: Path, keys: list[str]) -> None:
    values = {key: value for key, value in parse_env(path) if key is not None}
    for key in keys:
        if key not in values:
            state = "missing"
        elif values[key]:
            state = "present"
        else:
            state = "empty"
        print(f"{key}={state}")


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    set_parser = subparsers.add_parser("set")
    set_parser.add_argument("--file", required=True)
    set_parser.add_argument("--key", required=True)
    set_parser.add_argument("--value-stdin", action="store_true", required=True)

    inventory_parser = subparsers.add_parser("inventory")
    inventory_parser.add_argument("--file", required=True)
    inventory_parser.add_argument("keys", nargs="+")

    args = parser.parse_args()
    path = Path(args.file).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)

    if args.command == "set":
        value = sys.stdin.read()
        if value.endswith("\r\n"):
            value = value[:-2]
        elif value.endswith("\n"):
            value = value[:-1]
        if "\n" in value or "\r" in value:
            raise ValueError("Secret value must be a single line")
        atomic_set(path, args.key, value)
    else:
        inventory(path, args.keys)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
