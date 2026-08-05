from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from app.source_fetcher import GitSnapshotFetcher
from app.source_registry import get_profile, mirror_key


def git(args: list[str], cwd: Path, stdin: bytes | None = None, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=cwd, input=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=True, env=env,
    )
    return completed.stdout.decode("utf-8").strip()


class PersistentMirrorTest(unittest.TestCase):
    def test_snapshot_reads_protected_candidate_without_network(self) -> None:
        profile = get_profile("GENIE_MASTER")
        with tempfile.TemporaryDirectory() as temporary:
            mirror_root = Path(temporary)
            root = mirror_root / mirror_key(profile.repository)
            root.mkdir()
            git(["init", "--bare"], root)
            blob = git(["hash-object", "-w", "--stdin"], root, b"# offline evidence\n")
            tree = git(["mktree"], root, f"100644 blob {blob}\tREADME.md\n".encode())
            commit_env = {
                **os.environ,
                "GIT_AUTHOR_NAME": "TechFlow Test",
                "GIT_AUTHOR_EMAIL": "test@localhost",
                "GIT_COMMITTER_NAME": "TechFlow Test",
                "GIT_COMMITTER_EMAIL": "test@localhost",
            }
            commit = git(["commit-tree", tree, "-m", "offline snapshot"], root, env=commit_env)
            ref = f"refs/techflow/candidates/{profile.profile_id.lower()}/{commit}"
            git(["update-ref", ref, commit], root)

            fetcher = GitSnapshotFetcher(mirror_root)
            with fetcher.open_snapshot(profile, commit) as snapshot:
                entries = snapshot.entries()
                self.assertEqual(["README.md"], [entry.path for entry in entries])
                self.assertEqual(b"# offline evidence\n", snapshot.read_blob(blob))


if __name__ == "__main__":
    unittest.main()
