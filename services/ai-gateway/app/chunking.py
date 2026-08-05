"""Deterministic document and source-code chunking for Issue #43.

The parser consumes verified UTF-8 text only. It never imports, builds, tests, or
executes repository content. Tree-sitter is optional at process start so the
deterministic fallback remains available during local development and recovery.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import PurePosixPath
import re
from typing import Iterable
from uuid import UUID, uuid5


PARSER_PROFILE_ID = "TREE_SITTER_V1"
FALLBACK_MAX_LINES = 160
FALLBACK_OVERLAP_LINES = 20
MAX_EMBEDDING_INPUT_BYTES = 24 * 1024
_CHUNK_NAMESPACE = UUID("43000000-0000-0000-0000-000000000001")
_SYMBOL_NAMESPACE = UUID("43000000-0000-0000-0000-000000000002")
_RELATION_NAMESPACE = UUID("43000000-0000-0000-0000-000000000003")

_LANGUAGE_BY_SUFFIX = {
    ".java": "java", ".py": "python", ".js": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "tsx", ".vue": "vue", ".go": "go", ".c": "c",
    ".cc": "cpp", ".cpp": "cpp", ".h": "cpp", ".hpp": "cpp", ".sh": "bash",
    ".bash": "bash", ".rb": "ruby", ".rs": "rust", ".cs": "csharp",
}
_MARKDOWN_SUFFIXES = {".md", ".mdx", ".adoc", ".rst"}
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_PACKAGE = re.compile(r"(?m)^\s*(?:package|namespace)\s+([A-Za-z_][\w.]*)")
_INHERITANCE = re.compile(
    r"\b(?:class|interface)\s+([A-Za-z_]\w*)\s+(?:extends|implements|:)\s+([A-Za-z_][\w.]*)"
)
_REFERENCE = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
_REFERENCE_STOP = {
    "if", "for", "while", "switch", "catch", "return", "sizeof", "new", "print", "echo",
    "function", "def", "class", "super", "this",
}


@dataclass(frozen=True)
class ChunkRecord:
    id: UUID
    source_version_id: UUID
    source_kind: str
    path: str
    path_hash: str
    symbol: str | None
    start_line: int
    end_line: int
    content: str
    content_hash: str
    parser_status: str
    parser_profile_id: str
    chunk_index: int


@dataclass(frozen=True)
class SymbolRecord:
    id: UUID
    source_version_id: UUID
    chunk_id: UUID | None
    language: str
    package_name: str | None
    qualified_name: str
    signature: str | None
    path: str
    start_line: int
    end_line: int


@dataclass(frozen=True)
class RelationRecord:
    id: UUID
    source_version_id: UUID
    from_symbol_id: UUID
    to_qualified_name: str
    relation_type: str
    confidence: float


@dataclass(frozen=True)
class ParsedFile:
    chunks: tuple[ChunkRecord, ...]
    symbols: tuple[SymbolRecord, ...]
    relations: tuple[RelationRecord, ...]
    parser_status: str


def _stable_uuid(namespace: UUID, *parts: object) -> UUID:
    return uuid5(namespace, "\0".join(str(part) for part in parts))


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _path_hash(path: str) -> str:
    return hashlib.sha256(path.encode("utf-8")).hexdigest()


def _chunk_record(
    source_version_id: UUID,
    source_kind: str,
    path: str,
    symbol: str | None,
    start_line: int,
    end_line: int,
    content: str,
    parser_status: str,
    chunk_index: int,
) -> ChunkRecord:
    digest = _content_hash(content)
    chunk_id = _stable_uuid(
        _CHUNK_NAMESPACE, source_version_id, PARSER_PROFILE_ID, path, symbol or "", start_line, end_line, digest
    )
    return ChunkRecord(
        id=chunk_id,
        source_version_id=source_version_id,
        source_kind=source_kind,
        path=path,
        path_hash=_path_hash(path),
        symbol=symbol,
        start_line=start_line,
        end_line=end_line,
        content=content,
        content_hash=digest,
        parser_status=parser_status,
        parser_profile_id=PARSER_PROFILE_ID,
        chunk_index=chunk_index,
    )


def _windowed_chunks(
    source_version_id: UUID,
    source_kind: str,
    path: str,
    lines: list[str],
    base_line: int = 1,
    symbol: str | None = None,
    parser_status: str = "FALLBACK",
) -> list[ChunkRecord]:
    if not lines:
        lines = [""]
    chunks: list[ChunkRecord] = []
    start = 0
    while start < len(lines):
        end = min(len(lines), start + FALLBACK_MAX_LINES)
        while end > start + 1 and len("\n".join(lines[start:end]).encode("utf-8")) > MAX_EMBEDDING_INPUT_BYTES:
            end -= 1
        text = "\n".join(lines[start:end]).strip("\n")
        if not text:
            text = "\n"
        chunks.append(
            _chunk_record(
                source_version_id, source_kind, path, symbol, base_line + start,
                base_line + end - 1, text, parser_status, len(chunks),
            )
        )
        if end >= len(lines):
            break
        next_start = end - FALLBACK_OVERLAP_LINES
        start = next_start if next_start > start else end
    return chunks


def _markdown_chunks(source_version_id: UUID, source_kind: str, path: str, content: str) -> ParsedFile:
    lines = content.splitlines()
    headings = [(index, match.group(2).strip()) for index, line in enumerate(lines) if (match := _HEADING.match(line))]
    if not headings:
        chunks = _windowed_chunks(source_version_id, source_kind, path, lines)
        return ParsedFile(tuple(chunks), (), (), "FALLBACK")
    chunks: list[ChunkRecord] = []
    for position, (start, heading) in enumerate(headings):
        end = headings[position + 1][0] if position + 1 < len(headings) else len(lines)
        chunks.extend(
            _windowed_chunks(
                source_version_id, source_kind, path, lines[start:end], start + 1, heading, "PARSED"
            )
        )
    return ParsedFile(tuple(chunks), (), (), "PARSED")


def _tree_sitter_process(language: str, content: str):
    from tree_sitter_language_pack import PackConfig, ProcessConfig, configure, process

    cache_dir = os.getenv("TECHFLOW_TREE_SITTER_CACHE", "/opt/techflow/tree-sitter-parsers")
    configure(PackConfig(cache_dir=cache_dir))
    return process(
        content,
        ProcessConfig(
            language=language,
            structure=True,
            imports=True,
            exports=False,
            comments=False,
            docstrings=True,
            symbols=True,
            diagnostics=True,
            chunk_max_size=MAX_EMBEDDING_INPUT_BYTES,
        ),
    )


def _walk_structures(items: Iterable[object]) -> Iterable[object]:
    for item in items:
        yield item
        yield from _walk_structures(getattr(item, "children", ()) or ())


def _tree_sitter_chunks(
    source_version_id: UUID,
    source_kind: str,
    path: str,
    content: str,
    language: str,
) -> ParsedFile:
    result = _tree_sitter_process(language, content)
    raw_chunks = list(getattr(result, "chunks", ()) or ())
    if not raw_chunks:
        raise RuntimeError("tree-sitter produced no chunks")
    chunks: list[ChunkRecord] = []
    for raw in raw_chunks:
        metadata = getattr(raw, "metadata", None)
        context = list(getattr(metadata, "context_path", ()) or ())
        defined = list(getattr(metadata, "symbols_defined", ()) or ())
        symbol = context[-1] if context else (defined[0] if defined else None)
        start_line = int(getattr(raw, "start_line", 0)) + 1
        end_line = max(start_line, int(getattr(raw, "end_line", start_line - 1)) + 1)
        text = str(getattr(raw, "content", ""))
        if not text.strip():
            continue
        chunks.append(
            _chunk_record(
                source_version_id, source_kind, path, symbol, start_line, end_line, text, "PARSED", len(chunks)
            )
        )
    if not chunks:
        raise RuntimeError("tree-sitter produced only empty chunks")

    package_match = _PACKAGE.search(content)
    package_name = package_match.group(1) if package_match else None
    file_qualified_name = f"{path}::FILE"
    file_symbol = SymbolRecord(
        id=_stable_uuid(_SYMBOL_NAMESPACE, source_version_id, file_qualified_name, 1),
        source_version_id=source_version_id,
        chunk_id=chunks[0].id,
        language=language,
        package_name=package_name,
        qualified_name=file_qualified_name,
        signature=None,
        path=path,
        start_line=1,
        end_line=max(1, len(content.splitlines())),
    )
    symbols: list[SymbolRecord] = [file_symbol]
    seen: set[tuple[str, int]] = {(file_qualified_name, 1)}
    for item in _walk_structures(getattr(result, "structure", ()) or ()):
        name = getattr(item, "name", None)
        span = getattr(item, "span", None)
        if not name or span is None:
            continue
        start_line = int(getattr(span, "start_line", 0)) + 1
        end_line = max(start_line, int(getattr(span, "end_line", start_line - 1)) + 1)
        qualified = ".".join(filter(None, (package_name, str(name)))) if package_name else f"{path}::{name}"
        if (qualified, start_line) in seen:
            continue
        seen.add((qualified, start_line))
        matching = next((chunk for chunk in chunks if chunk.start_line <= start_line <= chunk.end_line), chunks[0])
        symbols.append(
            SymbolRecord(
                id=_stable_uuid(_SYMBOL_NAMESPACE, source_version_id, qualified, path, start_line),
                source_version_id=source_version_id,
                chunk_id=matching.id,
                language=language,
                package_name=package_name,
                qualified_name=qualified,
                signature=getattr(item, "signature", None),
                path=path,
                start_line=start_line,
                end_line=end_line,
            )
        )

    relations: list[RelationRecord] = []
    relation_keys: set[tuple[UUID, str, str]] = set()

    def add_relation(from_symbol: SymbolRecord, target: str, kind: str, confidence: float) -> None:
        clean = target.strip()
        key = (from_symbol.id, clean, kind)
        if not clean or key in relation_keys:
            return
        relation_keys.add(key)
        relations.append(
            RelationRecord(
                id=_stable_uuid(_RELATION_NAMESPACE, source_version_id, from_symbol.id, clean, kind),
                source_version_id=source_version_id,
                from_symbol_id=from_symbol.id,
                to_qualified_name=clean,
                relation_type=kind,
                confidence=confidence,
            )
        )

    for symbol in symbols[1:]:
        add_relation(file_symbol, symbol.qualified_name, "DECLARATION", 1.0)
    for imported in getattr(result, "imports", ()) or ():
        add_relation(file_symbol, str(getattr(imported, "source", "")), "IMPORT", 0.95)
    by_short_name = {symbol.qualified_name.rsplit(".", 1)[-1].split("::")[-1]: symbol for symbol in symbols[1:]}
    for child, parent in _INHERITANCE.findall(content):
        add_relation(by_short_name.get(child, file_symbol), parent, "INHERITANCE", 0.9)
    for reference in sorted(set(_REFERENCE.findall(content)) - _REFERENCE_STOP):
        add_relation(file_symbol, reference, "REFERENCE", 0.55)

    return ParsedFile(tuple(chunks), tuple(symbols), tuple(relations), "PARSED")


def chunk_file(
    source_version_id: UUID,
    source_kind: str,
    path: str,
    content: str,
) -> ParsedFile:
    """Parse one verified file and fall back deterministically on any parser error."""

    suffix = PurePosixPath(path).suffix.lower()
    if suffix in _MARKDOWN_SUFFIXES:
        return _markdown_chunks(source_version_id, source_kind, path, content)
    language = _LANGUAGE_BY_SUFFIX.get(suffix)
    if language:
        try:
            return _tree_sitter_chunks(source_version_id, source_kind, path, content, language)
        except Exception:
            pass
    chunks = _windowed_chunks(source_version_id, source_kind, path, content.splitlines())
    return ParsedFile(tuple(chunks), (), (), "FALLBACK")
