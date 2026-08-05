"""Source discovery and pinned snapshot scan orchestration."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .source_fetcher import SnapshotFetcher
from .source_policy import ScanResult, classify_path, scan_blob, snapshot_hash
from .source_registry import SourceProfile


class SourcePipeline:
    def __init__(self, fetcher: SnapshotFetcher) -> None:
        self.fetcher = fetcher

    def discover(self, profile: SourceProfile) -> str:
        return self.fetcher.resolve_head(profile)

    def scan(self, profile: SourceProfile, commit: str) -> dict[str, Any]:
        results: list[ScanResult] = []
        with self.fetcher.open_snapshot(profile, commit) as snapshot:
            for entry in snapshot.entries():
                metadata_result = classify_path(profile, entry)
                if metadata_result is not None:
                    results.append(metadata_result)
                    continue
                results.append(scan_blob(profile, entry, snapshot.read_blob(entry.object_id)))
            tree_sha = snapshot.tree_sha
        eligible = sum(item.decision == "ELIGIBLE" for item in results)
        excluded = sum(item.decision == "EXCLUDED" for item in results)
        blocking = sum(item.blocking for item in results)
        return {
            "commit": commit,
            "treeSha": tree_sha,
            "snapshotHash": snapshot_hash(profile.profile_id, commit, tree_sha, results),
            "candidateFileCount": len(results),
            "eligibleFileCount": eligible,
            "excludedFileCount": excluded,
            "blockingViolationCount": blocking,
            "files": [asdict(item) for item in results],
        }
