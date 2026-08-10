from __future__ import annotations

import unittest
from unittest.mock import patch
from uuid import uuid4

from app.chunking import (
    FALLBACK_MAX_LINES,
    FALLBACK_OVERLAP_LINES,
    MAX_EMBEDDING_INPUT_BYTES,
    MAX_QUALIFIED_NAME_CHARS,
    _bounded_qualified_name,
    _chunk_record,
    _dedupe_chunks,
    chunk_file,
)


class ChunkingTest(unittest.TestCase):
    def test_markdown_heading_chunks_are_deterministic(self) -> None:
        version_id = uuid4()
        source = "# 설치\n안내\n## 점검\n명령"
        first = chunk_file(version_id, "DOCUMENTATION", "README.md", source)
        second = chunk_file(version_id, "DOCUMENTATION", "README.md", source)
        self.assertEqual([item.id for item in first.chunks], [item.id for item in second.chunks])
        self.assertEqual(["설치", "점검"], [item.symbol for item in first.chunks])

    def test_fallback_windows_overlap_without_executing_content(self) -> None:
        marker = "raise RuntimeError('must never execute')"
        source = "\n".join([marker, *[f"line-{index}" for index in range(FALLBACK_MAX_LINES + 30)]])
        parsed = chunk_file(uuid4(), "SOURCE_CODE", "payload.unknown", source)
        self.assertEqual("FALLBACK", parsed.parser_status)
        self.assertEqual(2, len(parsed.chunks))
        self.assertEqual(FALLBACK_OVERLAP_LINES, parsed.chunks[0].end_line - parsed.chunks[1].start_line + 1)

    def test_parser_error_falls_back_closed(self) -> None:
        with patch("app.chunking._tree_sitter_process", side_effect=RuntimeError("parser unavailable")):
            parsed = chunk_file(uuid4(), "SOURCE_CODE", "main.py", "def ok():\n    return True\n")
        self.assertEqual("FALLBACK", parsed.parser_status)
        self.assertEqual(1, len(parsed.chunks))

    def test_single_long_utf8_line_is_split_below_provider_limit(self) -> None:
        source = "가" * 10000
        parsed = chunk_file(uuid4(), "SOURCE_CODE", "payload.unknown", source)
        self.assertGreater(len(parsed.chunks), 1)
        self.assertTrue(all(len(item.content.encode("utf-8")) <= MAX_EMBEDDING_INPUT_BYTES for item in parsed.chunks))
        self.assertEqual(source, "".join(item.content for item in parsed.chunks))

    def test_blank_file_produces_no_embedding_chunk(self) -> None:
        parsed = chunk_file(uuid4(), "SOURCE_CODE", "empty.js", " \n\t\n")
        self.assertEqual((), parsed.chunks)
        self.assertEqual("FALLBACK", parsed.parser_status)

    def test_long_parser_name_is_bounded_with_stable_hash_suffix(self) -> None:
        value = "dependency." + ("segment" * 300)
        first = _bounded_qualified_name(value)
        second = _bounded_qualified_name(value)
        self.assertEqual(MAX_QUALIFIED_NAME_CHARS, len(first))
        self.assertEqual(first, second)
        self.assertRegex(first, r"…#[0-9a-f]{16}$")

    def test_overlapping_parser_nodes_follow_database_chunk_uniqueness(self) -> None:
        version_id = uuid4()
        first = _chunk_record(version_id, "SOURCE_CODE", "Main.java", "Main", 1, 3, "class Main {}", "PARSED", 0)
        duplicate = _chunk_record(
            version_id, "SOURCE_CODE", "Main.java", "MainAlias", 1, 3, "class Main {}", "PARSED", 1
        )
        retained = _dedupe_chunks((first, duplicate))
        self.assertEqual([first.id], [item.id for item in retained])


if __name__ == "__main__":
    unittest.main()
