"""Pinned, no-checkout Git object reader used by the Issue #42 scanner."""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Protocol

from .source_policy import TreeEntry
from .source_registry import SourceProfile
from .store import InvalidBoundaryError, StoreError


SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class FetchError(StoreError):
    code = "SOURCE_FETCH_FAILED"
    http_status = 502


class HeadMovedError(StoreError):
    code = "SOURCE_HEAD_MOVED"
    http_status = 409


class Snapshot(Protocol):
    commit: str
    tree_sha: str

    def entries(self) -> list[TreeEntry]: ...
    def read_blob(self, object_id: str) -> bytes: ...


class SnapshotFetcher(Protocol):
    def resolve_head(self, profile: SourceProfile) -> str: ...
    def open_snapshot(self, profile: SourceProfile, commit: str) -> AbstractContextManager[Snapshot]: ...


def _safe_env() -> dict[str, str]:
    env = {
        "PATH": os.environ.get("PATH", ""),
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_LFS_SKIP_SMUDGE": "1",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }
    return {key: value for key, value in env.items() if value}


def _run(args: list[str], cwd: Path | None = None, binary: bool = False) -> bytes | str:
    completed = subprocess.run(
        args,
        cwd=cwd,
        env=_safe_env(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=300,
    )
    if completed.returncode:
        raise FetchError(f"safe git operation failed: {args[1] if len(args) > 1 else 'git'}")
    return completed.stdout if binary else completed.stdout.decode("utf-8", errors="strict")


@dataclass
class GitSnapshot(AbstractContextManager["GitSnapshot"]):
    root: Path
    commit: str
    tree_sha: str
    _temporary: tempfile.TemporaryDirectory[str]

    def __exit__(self, exc_type, exc, tb) -> None:
        self._temporary.cleanup()

    def entries(self) -> list[TreeEntry]:
        output = _run(["git", "ls-tree", "-r", "-l", "-z", self.commit], cwd=self.root, binary=True)
        assert isinstance(output, bytes)
        entries: list[TreeEntry] = []
        for record in output.split(b"\x00"):
            if not record:
                continue
            metadata, raw_path = record.split(b"\t", 1)
            mode, object_type, object_id, raw_size = metadata.decode("ascii").split()
            path = raw_path.decode("utf-8", errors="strict")
            size = None if raw_size == "-" else int(raw_size)
            entries.append(TreeEntry(path, object_id, object_type, mode, size))
        return entries

    def read_blob(self, object_id: str) -> bytes:
        if not SHA_PATTERN.fullmatch(object_id):
            raise InvalidBoundaryError("invalid blob object id")
        output = _run(["git", "cat-file", "blob", object_id], cwd=self.root, binary=True)
        assert isinstance(output, bytes)
        return output


class GitSnapshotFetcher:
    """Fetch only an allowlisted branch into a temporary bare repository.

    No checkout, hook, smudge filter, submodule update, build, test, or source
    execution is performed. The discovered commit must still be the branch head
    when the pinned snapshot is opened.
    """

    @staticmethod
    def _url(profile: SourceProfile) -> str:
        return f"https://github.com/{profile.repository}.git"

    def resolve_head(self, profile: SourceProfile) -> str:
        output = _run(["git", "ls-remote", "--heads", "--exit-code", self._url(profile), f"refs/heads/{profile.branch}"])
        assert isinstance(output, str)
        rows = [line.split() for line in output.splitlines() if line.strip()]
        if len(rows) != 1 or not SHA_PATTERN.fullmatch(rows[0][0]):
            raise FetchError("allowlisted branch head was not resolved uniquely")
        return rows[0][0]

    def open_snapshot(self, profile: SourceProfile, commit: str) -> GitSnapshot:
        if not SHA_PATTERN.fullmatch(commit):
            raise InvalidBoundaryError("invalid pinned commit")
        temporary = tempfile.TemporaryDirectory(
            prefix="techflow-source-", dir=os.getenv("TECHFLOW_SOURCE_TMPDIR") or None
        )
        root = Path(temporary.name) / "objects.git"
        root.mkdir(mode=0o700)
        empty_hooks = Path(temporary.name) / "hooks-disabled"
        empty_hooks.mkdir(mode=0o500)
        safe_options = [
            "-c", f"core.hooksPath={empty_hooks}",
            "-c", "protocol.file.allow=never",
            "-c", "protocol.ext.allow=never",
            "-c", "fetch.fsckObjects=true",
        ]
        try:
            _run(["git", *safe_options, "init", "--bare", str(root)])
            _run(["git", *safe_options, "remote", "add", "origin", self._url(profile)], cwd=root)
            _run(
                ["git", *safe_options, "fetch", "--depth=1", "--no-tags", "origin", f"refs/heads/{profile.branch}"],
                cwd=root,
            )
            fetched = str(_run(["git", "rev-parse", "FETCH_HEAD"], cwd=root)).strip()
            if fetched != commit:
                raise HeadMovedError("branch head changed after candidate registration")
            tree_sha = str(_run(["git", "rev-parse", f"{commit}^{{tree}}"], cwd=root)).strip()
            if not SHA_PATTERN.fullmatch(tree_sha):
                raise FetchError("invalid root tree object id")
            return GitSnapshot(root, commit, tree_sha, temporary)
        except Exception:
            temporary.cleanup()
            raise
