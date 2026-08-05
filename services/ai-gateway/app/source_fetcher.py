"""Persistent, pinned, no-checkout Git object reader for Issue #42."""

from __future__ import annotations

from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
import re
import subprocess
from typing import BinaryIO, Iterator, Protocol

from .source_policy import TreeEntry
from .source_registry import SourceProfile, mirror_key
from .store import InvalidBoundaryError, StoreError


SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class FetchError(StoreError):
    code = "SOURCE_FETCH_FAILED"
    http_status = 502


class HeadMovedError(StoreError):
    """Kept for API compatibility with earlier Issue #42 clients."""

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


def _lock_file(handle: BinaryIO) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)


def _unlock_file(handle: BinaryIO) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def _mirror_lock(path: Path) -> Iterator[BinaryIO]:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    handle = path.open("a+b")
    if path.stat().st_size == 0:
        handle.write(b"0")
        handle.flush()
    _lock_file(handle)
    try:
        yield handle
    finally:
        _unlock_file(handle)
        handle.close()


@dataclass
class GitSnapshot(AbstractContextManager["GitSnapshot"]):
    root: Path
    commit: str
    tree_sha: str
    _lock_handle: BinaryIO

    def __exit__(self, exc_type, exc, tb) -> None:
        _unlock_file(self._lock_handle)
        self._lock_handle.close()

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
    """Maintain one persistent bare mirror per allowlisted repository.

    Network access is limited to ``resolve_head``. ``open_snapshot`` is a
    local-only read from a protected candidate ref, so scans continue when
    GitHub is temporarily unavailable. No checkout, hook, smudge filter,
    submodule update, build, test, or source execution is performed.
    """

    def __init__(self, mirror_root: str | Path | None = None) -> None:
        configured = mirror_root or os.getenv("TECHFLOW_SOURCE_MIRROR_ROOT") or "/var/lib/techflow-source-mirrors"
        self.mirror_root = Path(configured)

    @staticmethod
    def _url(profile: SourceProfile) -> str:
        return f"https://github.com/{profile.repository}.git"

    def _mirror_path(self, profile: SourceProfile) -> Path:
        return self.mirror_root / mirror_key(profile.repository)

    def _lock_path(self, profile: SourceProfile) -> Path:
        return self.mirror_root / ".locks" / f"{mirror_key(profile.repository)}.lock"

    @staticmethod
    def _head_ref(profile: SourceProfile) -> str:
        return f"refs/techflow/heads/{profile.profile_id.lower()}"

    @staticmethod
    def _candidate_ref(profile: SourceProfile, commit: str) -> str:
        return f"refs/techflow/candidates/{profile.profile_id.lower()}/{commit}"

    def _safe_options(self) -> list[str]:
        hooks = self.mirror_root / ".hooks-disabled"
        hooks.mkdir(parents=True, exist_ok=True, mode=0o500)
        return [
            "-c", f"core.hooksPath={hooks}",
            "-c", "protocol.file.allow=never",
            "-c", "protocol.ext.allow=never",
            "-c", "fetch.fsckObjects=true",
        ]

    def resolve_head(self, profile: SourceProfile) -> str:
        self.mirror_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        root = self._mirror_path(profile)
        with _mirror_lock(self._lock_path(profile)):
            safe_options = self._safe_options()
            if not root.exists():
                _run(["git", *safe_options, "init", "--bare", str(root)])
                _run(["git", *safe_options, "remote", "add", "origin", self._url(profile)], cwd=root)
            else:
                bare = str(_run(["git", "rev-parse", "--is-bare-repository"], cwd=root)).strip()
                remote = str(_run(["git", "config", "--get", "remote.origin.url"], cwd=root)).strip()
                if bare != "true" or remote != self._url(profile):
                    raise FetchError("persistent mirror identity validation failed")

            head_ref = self._head_ref(profile)
            _run(
                [
                    "git", *safe_options, "fetch", "--depth=1", "--no-tags", "--prune",
                    "origin", f"+refs/heads/{profile.branch}:{head_ref}",
                ],
                cwd=root,
            )
            commit = str(_run(["git", "rev-parse", f"{head_ref}^{{commit}}"], cwd=root)).strip()
            if not SHA_PATTERN.fullmatch(commit):
                raise FetchError("allowlisted branch head was not resolved uniquely")
            _run(["git", "update-ref", self._candidate_ref(profile, commit), commit], cwd=root)
            _run(["git", "fsck", "--connectivity-only", "--no-dangling", commit], cwd=root)
            _run(["git", "gc", "--auto", "--quiet"], cwd=root)
            return commit

    def open_snapshot(self, profile: SourceProfile, commit: str) -> GitSnapshot:
        if not SHA_PATTERN.fullmatch(commit):
            raise InvalidBoundaryError("invalid pinned commit")
        root = self._mirror_path(profile)
        lock_path = self._lock_path(profile)
        lock_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        handle = lock_path.open("a+b")
        if lock_path.stat().st_size == 0:
            handle.write(b"0")
            handle.flush()
        _lock_file(handle)
        try:
            if not root.is_dir():
                raise FetchError("persistent mirror has not been synchronized")
            candidate = str(_run(["git", "rev-parse", self._candidate_ref(profile, commit)], cwd=root)).strip()
            if candidate != commit:
                raise FetchError("pinned candidate ref is missing from persistent mirror")
            _run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=root)
            tree_sha = str(_run(["git", "rev-parse", f"{commit}^{{tree}}"], cwd=root)).strip()
            if not SHA_PATTERN.fullmatch(tree_sha):
                raise FetchError("invalid root tree object id")
            return GitSnapshot(root, commit, tree_sha, handle)
        except Exception:
            _unlock_file(handle)
            handle.close()
            raise
