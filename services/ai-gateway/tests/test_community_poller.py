from __future__ import annotations

import importlib.util
from email.message import Message
from io import BytesIO
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    "poll_flarum", Path(__file__).parents[1] / "scripts" / "poll_flarum.py"
)
poll_flarum = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(poll_flarum)


class FakeResponse(BytesIO):
    def __init__(self, data: bytes, *, content_type: str = "text/plain", content_length: int | None = None) -> None:
        super().__init__(data)
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        if content_length is not None:
            self.headers["Content-Length"] = str(content_length)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


class CommunityPollerTests(unittest.TestCase):
    def test_only_unanswered_discussions_are_normalized(self) -> None:
        payload = {
            "data": [
                {"type": "discussions", "id": "10", "attributes": {"title": "질문", "commentCount": 1},
                 "relationships": {"firstPost": {"data": {"type": "posts", "id": "100"}},
                                   "user": {"data": {"type": "users", "id": "7"}},
                                   "tags": {"data": [{"type": "tags", "id": "3"}]}}},
                {"type": "discussions", "id": "11", "attributes": {"title": "답변됨", "commentCount": 2},
                 "relationships": {}},
            ],
            "included": [
                {"type": "posts", "id": "100", "attributes": {"contentHtml": "<p>VM 오류입니다.</p><a href='/assets/a.log'>log</a>"}},
                {"type": "users", "id": "7", "attributes": {"username": "tester"}},
                {"type": "tags", "id": "3", "attributes": {"slug": "mold"}},
            ],
        }
        events = poll_flarum.normalize(payload, "https://community.ablecloud.io")
        self.assertEqual(1, len(events))
        self.assertEqual("10", events[0]["discussionId"])
        self.assertEqual(["mold"], events[0]["tagSlugs"])
        self.assertEqual(["/assets/a.log"], events[0]["attachmentUrls"])

    def test_html_parser_does_not_execute_or_expand_markup(self) -> None:
        parser = poll_flarum.ContentParser()
        parser.feed("<p>질문</p><script>ignore()</script>")
        self.assertEqual(["질문", "ignore()"], parser.text)

    def test_attachment_policy_accepts_exact_boundary_and_rejects_one_byte_over(self) -> None:
        exact = b"A" * 2048
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "a.log"
            with patch.object(poll_flarum.urllib.request, "urlopen", return_value=FakeResponse(exact)):
                size, media_type, _, _ = poll_flarum._read_attachment(
                    poll_flarum.urllib.request.Request("https://community.ablecloud.io/a.log"),
                    destination, filename="a.log", max_bytes=2048, max_archive_bytes=4096,
                    timeout=5, retries=0,
                )
            self.assertEqual(2048, size)
            self.assertEqual(exact, destination.read_bytes())
            self.assertEqual("text/plain", media_type)

            with patch.object(poll_flarum.urllib.request, "urlopen", return_value=FakeResponse(exact + b"!")):
                with self.assertRaisesRegex(ValueError, "size"):
                    poll_flarum._read_attachment(
                        poll_flarum.urllib.request.Request("https://community.ablecloud.io/a.log"),
                        destination, filename="a.log", max_bytes=2048, max_archive_bytes=4096,
                        timeout=5, retries=0,
                    )

    def test_content_length_is_rejected_before_body_download(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.object(
            poll_flarum.urllib.request, "urlopen", return_value=FakeResponse(
                b"", content_type="application/zip", content_length=4097,
            ),
        ):
            with self.assertRaisesRegex(ValueError, "size"):
                poll_flarum._read_attachment(
                    poll_flarum.urllib.request.Request("https://community.ablecloud.io/a.zip"),
                    Path(directory) / "a.zip", filename="a.zip", max_bytes=2048,
                    max_archive_bytes=4096, timeout=5, retries=0,
                )

    def test_attachment_policy_environment_is_bounded(self) -> None:
        with patch.dict(os.environ, {"TECHFLOW_COMMUNITY_ATTACHMENT_MAX_BYTES": str(1024 * 1024 * 1024 + 1)}, clear=False):
            with self.assertRaises(RuntimeError):
                poll_flarum._attachment_policy()

    def test_external_attachment_is_skipped_with_understandable_warning(self) -> None:
        event = {"attachmentUrls": ["https://example.invalid/secret.log"]}
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"TECHFLOW_COMMUNITY_ATTACHMENT_TMP_DIR": directory}, clear=False,
        ):
            ids = poll_flarum.upload_artifacts(
                event, "http://gateway:8090", "http://172.16.0.234",
                "https://community.ablecloud.io", "runtime-token", "community-test-0001",
            )
        self.assertEqual([], ids)
        self.assertIn("Community 외부 주소", event["artifactWarnings"][0])

    def test_archive_media_type_is_normalized_from_download_filename(self) -> None:
        self.assertEqual("application/zip", poll_flarum._normalized_attachment_media_type("support.zip", "application/force-download"))
        self.assertEqual("application/gzip", poll_flarum._normalized_attachment_media_type("support.tar.gz", "application/octet-stream"))
        self.assertEqual("application/gzip", poll_flarum._normalized_attachment_media_type("agent.log.gz", "application/octet-stream"))


if __name__ == "__main__":
    unittest.main()
