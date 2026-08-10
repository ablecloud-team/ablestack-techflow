from __future__ import annotations

import unittest
from unittest.mock import patch
from uuid import uuid4

from app.chunking import FALLBACK_MAX_LINES, FALLBACK_OVERLAP_LINES, chunk_file


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


if __name__ == "__main__":
    unittest.main()
