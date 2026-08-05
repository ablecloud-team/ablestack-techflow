"""Fail-closed path and text quarantine policy for pinned Git objects."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import PurePosixPath
import re
from typing import Iterable

from .source_registry import SourceProfile


MAX_FILE_BYTES = 1024 * 1024
ALLOWED_EXTENSIONS = {
    ".java", ".py", ".js", ".jsx", ".ts", ".tsx", ".vue", ".go", ".rb", ".groovy",
    ".cs", ".sh", ".bash", ".c", ".cc", ".cpp", ".h", ".hpp", ".rs", ".ps1", ".cmd",
    ".bat", ".html", ".htm", ".css", ".scss", ".sass", ".less", ".hbs", ".xml", ".sql",
    ".yaml", ".yml", ".properties", ".json", ".toml", ".ini", ".conf", ".cfg", ".service",
    ".spec", ".ks", ".repo", ".j2", ".tmpl", ".in", ".md", ".mdx", ".adoc", ".rst",
}
EXCLUDED_SEGMENTS = {"target", "build", "dist", "node_modules", "vendor", "third_party", "generated", "gen"}
BUILD_SCHEMA_EXTENSIONS = {
    ".xml", ".sql", ".yaml", ".yml", ".properties", ".json", ".toml", ".ini", ".conf",
    ".cfg", ".service", ".spec", ".ks", ".repo", ".j2", ".tmpl", ".in",
}
DOCUMENT_EXTENSIONS = {".md", ".mdx", ".adoc", ".rst"}


@dataclass(frozen=True)
class TreeEntry:
    path: str
    object_id: str
    object_type: str
    mode: str
    size: int | None


@dataclass(frozen=True)
class ScanResult:
    path: str
    path_hash: str
    blob_sha: str | None
    content_hash: str | None
    size_bytes: int | None
    source_kind: str | None
    encoding: str | None
    decision: str
    rule_ids: tuple[str, ...]
    content: str | None = None

    @property
    def blocking(self) -> bool:
        return self.decision == "QUARANTINED"


def _path_hash(path: str) -> str:
    return hashlib.sha256(path.encode("utf-8")).hexdigest()


def _valid_path(path: str) -> bool:
    candidate = PurePosixPath(path)
    return bool(path) and "\\" not in path and not candidate.is_absolute() and ".." not in candidate.parts


def classify_path(profile: SourceProfile, entry: TreeEntry) -> ScanResult | None:
    path_hash = _path_hash(entry.path)
    if not _valid_path(entry.path):
        return ScanResult(entry.path, path_hash, None, None, entry.size, None, None, "QUARANTINED", ("PATH_TRAVERSAL",))
    if entry.object_type == "commit" or entry.mode == "160000":
        return ScanResult(entry.path, path_hash, None, None, entry.size, None, None, "QUARANTINED", ("SUBMODULE_FORBIDDEN",))
    if entry.mode == "120000":
        return ScanResult(entry.path, path_hash, entry.object_id, None, entry.size, None, None, "QUARANTINED", ("SYMLINK_FORBIDDEN",))
    if entry.object_type != "blob":
        return ScanResult(entry.path, path_hash, None, None, entry.size, None, None, "EXCLUDED", ("NON_BLOB",))
    lowered_parts = {part.lower() for part in PurePosixPath(entry.path).parts}
    if lowered_parts & EXCLUDED_SEGMENTS:
        return ScanResult(entry.path, path_hash, entry.object_id, None, entry.size, None, None, "EXCLUDED", ("GENERATED_OR_VENDOR_PATH",))
    suffix = PurePosixPath(entry.path).suffix.lower()
    if profile.docs_root and (not entry.path.startswith(profile.docs_root) or suffix != ".md"):
        return ScanResult(entry.path, path_hash, entry.object_id, None, entry.size, None, None, "EXCLUDED", ("DOCS_ROOT_ALLOWLIST",))
    if suffix not in ALLOWED_EXTENSIONS:
        return ScanResult(entry.path, path_hash, entry.object_id, None, entry.size, None, None, "EXCLUDED", ("EXTENSION_NOT_ALLOWED",))
    if entry.path.lower().endswith((".min.js", ".min.css")):
        return ScanResult(entry.path, path_hash, entry.object_id, None, entry.size, None, None, "EXCLUDED", ("MINIFIED_ASSET",))
    if entry.size is None or entry.size > MAX_FILE_BYTES:
        return ScanResult(entry.path, path_hash, entry.object_id, None, entry.size, None, None, "QUARANTINED", ("FILE_SIZE_LIMIT",))
    return None


_SECRET_PATTERNS = {
    "SECRET_PRIVATE_KEY": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "SECRET_GITHUB_TOKEN": re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b"),
    "SECRET_OPENAI_KEY": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "SECRET_AWS_ACCESS_KEY": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "SECRET_GENERIC_ASSIGNMENT": re.compile(
        r"(?im)^\s*(?:password|passwd|api[_-]?key|secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9/+_.:@-]{12,}"
    ),
}
_PII_PATTERNS = {
    "PII_KR_RRN": re.compile(r"\b\d{6}-?[1-4]\d{6}\b"),
    "PII_EMAIL": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
}
_PROMPT_PATTERNS = {
    "PROMPT_INJECTION_OVERRIDE": re.compile(r"(?i)ignore\s+(?:all\s+)?previous\s+instructions"),
    "PROMPT_INJECTION_SYSTEM": re.compile(r"(?i)(?:reveal|print|return)\s+(?:the\s+)?system\s+prompt"),
}


def _source_kind(path: str) -> str:
    lowered = path.lower()
    suffix = PurePosixPath(path).suffix.lower()
    parts = {part.lower() for part in PurePosixPath(path).parts}
    if "test" in parts or "tests" in parts or re.search(r"(?:^|[._-])test(?:[._-]|$)", PurePosixPath(path).name, re.I):
        return "TEST_CODE"
    if suffix in BUILD_SCHEMA_EXTENSIONS:
        return "BUILD_SCHEMA"
    if suffix in DOCUMENT_EXTENSIONS or "/docs/" in f"/{lowered}":
        return "DOCUMENTATION"
    return "SOURCE_CODE"


def scan_blob(profile: SourceProfile, entry: TreeEntry, raw: bytes) -> ScanResult:
    path_hash = _path_hash(entry.path)
    if len(raw) != entry.size or len(raw) > MAX_FILE_BYTES:
        return ScanResult(entry.path, path_hash, entry.object_id, None, len(raw), None, None, "QUARANTINED", ("BLOB_SIZE_MISMATCH",))
    if b"\x00" in raw:
        return ScanResult(entry.path, path_hash, entry.object_id, None, len(raw), None, None, "QUARANTINED", ("BINARY_CONTENT",))
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return ScanResult(entry.path, path_hash, entry.object_id, None, len(raw), None, None, "QUARANTINED", ("UTF8_REQUIRED",))
    rules: list[str] = []
    for rule_id, pattern in {**_SECRET_PATTERNS, **_PII_PATTERNS, **_PROMPT_PATTERNS}.items():
        if pattern.search(text):
            rules.append(rule_id)
    lines = text.splitlines() or [""]
    if len(lines) <= 3 and max(len(line) for line in lines) > 4000:
        rules.append("MINIFIED_CONTENT")
    if re.search(r"(?im)^\s*(?://|#|/\*)\s*(?:generated|auto-generated|do not edit)\b", text[:4096]):
        rules.append("GENERATED_CONTENT")
    content_hash = hashlib.sha256(raw).hexdigest()
    if rules:
        return ScanResult(
            entry.path, path_hash, entry.object_id, content_hash, len(raw), _source_kind(entry.path),
            "utf-8", "QUARANTINED", tuple(sorted(set(rules))), None,
        )
    return ScanResult(
        entry.path, path_hash, entry.object_id, content_hash, len(raw), _source_kind(entry.path),
        "utf-8", "ELIGIBLE", (), text,
    )


def snapshot_hash(profile_id: str, commit: str, tree_sha: str, results: Iterable[ScanResult]) -> str:
    digest = hashlib.sha256(f"{profile_id}\0{commit}\0{tree_sha}\0".encode("utf-8"))
    for result in sorted(results, key=lambda item: item.path):
        digest.update(
            "\0".join(
                (result.path, result.blob_sha or "", result.content_hash or "", result.decision, ",".join(result.rule_ids))
            ).encode("utf-8")
        )
        digest.update(b"\0")
    return digest.hexdigest()
