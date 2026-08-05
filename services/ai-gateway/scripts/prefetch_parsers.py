#!/usr/bin/env python3
"""Download pinned Tree-sitter parser binaries while the container image is built."""

from __future__ import annotations

import os

from tree_sitter_language_pack import PackConfig, configure, download, get_parser


LANGUAGES = ["bash", "c", "cpp", "csharp", "go", "java", "javascript", "python", "ruby", "rust", "tsx", "typescript", "vue"]


def main() -> int:
    cache = os.getenv("TECHFLOW_TREE_SITTER_CACHE", "/opt/techflow/tree-sitter-parsers")
    configure(PackConfig(cache_dir=cache))
    download(LANGUAGES)
    for language in LANGUAGES:
        get_parser(language)
    print(f"tree_sitter_parsers=ready count={len(LANGUAGES)} cache={cache}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
