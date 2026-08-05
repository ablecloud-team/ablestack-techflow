#!/usr/bin/env python3
"""Run a secret-safe discovery or pinned scan canary for one allowlisted profile."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.source_fetcher import GitSnapshotFetcher
from app.source_pipeline import SourcePipeline
from app.source_registry import SOURCE_PROFILES, get_profile


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("profile_id")
    parser.add_argument("--scan", action="store_true")
    args = parser.parse_args()
    pipeline = SourcePipeline(GitSnapshotFetcher())
    if args.profile_id == "ALL":
        if args.scan:
            raise SystemExit("ALL cannot be combined with --scan")
        values = []
        for profile in SOURCE_PROFILES.values():
            values.append(
                {
                    "sourceProfileId": profile.profile_id,
                    "repository": profile.repository,
                    "branch": profile.branch,
                    "commit": pipeline.discover(profile),
                }
            )
        print(json.dumps(values, sort_keys=True, separators=(",", ":")))
        return 0
    profile = get_profile(args.profile_id)
    commit = pipeline.discover(profile)
    result: dict[str, object] = {
        "sourceProfileId": profile.profile_id,
        "repository": profile.repository,
        "branch": profile.branch,
        "commit": commit,
    }
    if args.scan:
        report = pipeline.scan(profile, commit)
        result.update(
            {
                "treeSha": report["treeSha"],
                "snapshotHash": report["snapshotHash"],
                "candidateFileCount": report["candidateFileCount"],
                "eligibleFileCount": report["eligibleFileCount"],
                "excludedFileCount": report["excludedFileCount"],
                "blockingViolationCount": report["blockingViolationCount"],
            }
        )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
