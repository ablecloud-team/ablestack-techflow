#!/usr/bin/env python3
"""Validate Issue #20 links, checksums, page counts, deck, and secret hygiene."""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "output/issue-20-design-artifact-manifest.json"
BINARY_SUFFIXES = {".pdf", ".pptx"}
MARKDOWN = [
    ROOT / "README.md",
    ROOT / "docs/plans/techflow-product-roadmap.md",
    ROOT / "docs/adr/0008-techflow-rag-poc-architecture.md",
    ROOT / "docs/adr/0009-openai-runtime-integration.md",
    ROOT / "docs/plans/issue-20-rag-poc-design.md",
    ROOT / "docs/runbooks/rag-poc-development.md",
    ROOT / "docs/reports/issue-20-rag-poc-design-review.md",
]
SECRET_PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github-token": re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    "openai-key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "token-query": re.compile(r"[?&]token=(?:%22|%27|[\"'])?[A-Za-z0-9_-]{16,}"),
    "credential": re.compile(
        r"(?i)\b(?:password|api[_-]?key|api[_-]?secret)\s*[:=]\s*[\"'][^\"']{12,}[\"']"
    ),
}


def canonical(path: Path) -> bytes:
    data = path.read_bytes()
    if path.suffix.lower() in BINARY_SUFFIXES:
        return data
    return data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
assert manifest["issue"] == 20
assert manifest["status"] == "design-completed-approval-pending"
assert len(manifest["files"]) == 15
for item in manifest["files"]:
    path = ROOT / item["path"]
    assert path.is_file(), item["path"]
    content = canonical(path)
    assert len(content) == item["size"], item["path"]
    assert hashlib.sha256(content).hexdigest().upper() == item["sha256"], item["path"]

missing = []
checked_links = 0
link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
for markdown in MARKDOWN:
    for target in link_pattern.findall(markdown.read_text(encoding="utf-8")):
        checked_links += 1
        clean = target.strip().split("#", 1)[0]
        if clean and not clean.startswith(("http://", "https://", "mailto:")):
            if not (markdown.parent / clean).resolve().exists():
                missing.append(f"{markdown.relative_to(ROOT)} -> {target}")
assert not missing, "; ".join(missing)

hits = []
for item in manifest["files"]:
    path = ROOT / item["path"]
    if path.suffix.lower() in BINARY_SUFFIXES:
        continue
    text = path.read_text(encoding="utf-8")
    for name, pattern in SECRET_PATTERNS.items():
        if pattern.search(text):
            hits.append(f"{item['path']}:{name}")
assert not hits, "; ".join(hits)

assert len(PdfReader(str(ROOT / "output/pdf/techflow-rag-poc-design-report.pdf")).pages) == 10
assert len(PdfReader(str(ROOT / "output/pdf/techflow-rag-poc-design-presentation.pdf")).pages) == 10
with zipfile.ZipFile(ROOT / "output/presentation/techflow-rag-poc-design.pptx") as archive:
    slides = [name for name in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)]
    assert len(slides) == 10
    empty_placeholders = []
    for name in slides:
        root = ET.fromstring(archive.read(name))
        ns = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main", "a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
        for shape in root.findall(".//p:sp", ns):
            if shape.find("./p:nvSpPr/p:nvPr/p:ph", ns) is not None:
                text = "".join(node.text or "" for node in shape.findall(".//a:t", ns)).strip()
                if not text:
                    empty_placeholders.append(name)
    assert not empty_placeholders, f"empty placeholders: {empty_placeholders}"
    deck_text = "\n".join(archive.read(name).decode("utf-8", errors="ignore") for name in slides)
    for expected in ("OpenAI", "Responses", "Embeddings", "Tool 0"):
        assert expected in deck_text, f"deck missing {expected}"
print(f"artifacts=valid files=15 links={checked_links} secrets=0 report_pages=10 deck_pages=10 slides=10")
