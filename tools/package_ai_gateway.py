#!/usr/bin/env python3
"""Create a platform-neutral AI Gateway source archive from committed files."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import tarfile


REPO = Path(__file__).resolve().parents[1]
SOURCE_TREE = "services/ai-gateway"


def build_archive(output: Path, revision: str) -> None:
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "git",
            "-c",
            "core.autocrlf=false",
            "archive",
            "--format=tar.gz",
            f"--output={output}",
            f"{revision}:{SOURCE_TREE}",
        ],
        cwd=REPO,
        check=True,
    )
    with tarfile.open(output, "r:gz") as archive:
        invalid = []
        for member in archive.getmembers():
            if not member.isfile() or not member.name.endswith(".sh"):
                continue
            extracted = archive.extractfile(member)
            if extracted is not None and b"\r\n" in extracted.read():
                invalid.append(member.name)
    if invalid:
        output.unlink(missing_ok=True)
        raise RuntimeError(f"CRLF shell scripts in release archive: {invalid}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--revision", default="HEAD")
    args = parser.parse_args()
    build_archive(args.output, args.revision)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
