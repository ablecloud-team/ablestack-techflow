#!/usr/bin/env python3
"""Validate Issue #39 document links, checksums, page counts, and secret hygiene."""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = ROOT / "output" / "issue-39-artifact-manifest.json"
BINARY_SUFFIXES = {".pdf", ".pptx"}
MARKDOWN_FILES = [
    ROOT / "README.md",
    ROOT / "docs" / "plans" / "techflow-product-roadmap.md",
    ROOT / "docs" / "adr" / "0006-techflow-security-threat-model.md",
    ROOT / "docs" / "adr" / "0007-techflow-data-classification-retention.md",
    ROOT / "docs" / "runbooks" / "security-data-governance.md",
    ROOT / "docs" / "reports" / "issue-39-security-data-policy-validation.md",
]
SECRET_PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github-token": re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    "openai-key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "token-query": re.compile(r"[?&]token=(?:%22|%27|[\"'])?[A-Za-z0-9_-]{16,}"),
    "credential-assignment": re.compile(
        r"(?i)\b(?:password|api[_-]?key|api[_-]?secret)\s*[:=]\s*[\"'][^\"']{12,}[\"']"
    ),
}


def canonical(path: Path) -> bytes:
    data = path.read_bytes()
    if path.suffix.lower() in BINARY_SUFFIXES:
        return data
    return data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
assert manifest["issue"] == 39
assert manifest["status"] == "completed"
assert len(manifest["files"]) >= 14

for record in manifest["files"]:
    path = ROOT / record["path"]
    assert path.is_file(), f"missing artifact: {record['path']}"
    content = canonical(path)
    assert len(content) == record["size"], f"size mismatch: {record['path']}"
    assert hashlib.sha256(content).hexdigest().upper() == record["sha256"], (
        f"checksum mismatch: {record['path']}"
    )

missing_links: list[str] = []
link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
for markdown in MARKDOWN_FILES:
    text = markdown.read_text(encoding="utf-8")
    for target in link_pattern.findall(text):
        clean = target.strip().split("#", 1)[0]
        if not clean or clean.startswith(("http://", "https://", "mailto:")):
            continue
        resolved = (markdown.parent / clean).resolve()
        if not resolved.exists():
            missing_links.append(f"{markdown.relative_to(ROOT)} -> {target}")
assert not missing_links, "missing markdown links: " + "; ".join(missing_links)

secret_hits: list[str] = []
for record in manifest["files"]:
    path = ROOT / record["path"]
    if path.suffix.lower() in BINARY_SUFFIXES:
        continue
    text = path.read_text(encoding="utf-8")
    for name, pattern in SECRET_PATTERNS.items():
        if pattern.search(text):
            secret_hits.append(f"{record['path']}:{name}")
assert not secret_hits, "potential secret patterns: " + "; ".join(secret_hits)

report_pdf = ROOT / "output" / "pdf" / "techflow-security-data-policy-report.pdf"
deck_pdf = ROOT / "output" / "pdf" / "techflow-security-data-policy-presentation.pdf"
assert len(PdfReader(str(report_pdf)).pages) == 9
assert len(PdfReader(str(deck_pdf)).pages) == 10

pptx = ROOT / "output" / "presentation" / "techflow-security-data-policy.pptx"
with zipfile.ZipFile(pptx) as archive:
    slide_parts = [
        name for name in archive.namelist()
        if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
    ]
    assert len(slide_parts) == 10

print(
    "artifacts=valid "
    f"files={len(manifest['files'])} links={len(MARKDOWN_FILES)} "
    "secrets=0 report_pages=9 deck_pages=10 slides=10"
)
