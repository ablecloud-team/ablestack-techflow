#!/usr/bin/env python3
"""Validate Issue #42 checksums, links, pages, deck text, and secret hygiene."""

import hashlib
import json
import re
import zipfile
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "output/issue-42-artifact-manifest.json"
BINARY = {".pdf", ".pptx"}
MARKDOWN = [
    ROOT / "README.md",
    ROOT / "docs/plans/techflow-product-roadmap.md",
    ROOT / "docs/runbooks/rag-poc-development.md",
    ROOT / "docs/runbooks/source-registry-quarantine.md",
    ROOT / "docs/reports/issue-42-source-registry-validation.md",
    ROOT / "services/ai-gateway/README.md",
]
SECRET_PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github-token": re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    "openai-key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "token-query": re.compile(r"[?&]token=(?:%22|%27|[\"'])?[A-Za-z0-9_-]{16,}"),
    "credential": re.compile(r"(?i)\b(?:password|api[_-]?key|api[_-]?secret)\s*[:=]\s*[\"'][^\"']{12,}[\"']"),
}


def canonical(path):
    data = path.read_bytes()
    if path.suffix.lower() in BINARY:
        return data
    return data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
assert manifest["issue"] == 42
assert manifest["status"] == "implemented-deployed-and-validated"
assert manifest["initialSourceReviewer"] == "dhslove"
assert len(manifest["files"]) == 45
for item in manifest["files"]:
    path = ROOT / item["path"]
    assert path.is_file(), item["path"]
    content = canonical(path)
    assert len(content) == item["size"], item["path"]
    assert hashlib.sha256(content).hexdigest().upper() == item["sha256"], item["path"]

missing = []
checked_links = 0
for markdown in MARKDOWN:
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", markdown.read_text(encoding="utf-8")):
        checked_links += 1
        clean = target.strip().split("#", 1)[0]
        if clean and not clean.startswith(("http://", "https://", "mailto:")) and not (markdown.parent / clean).resolve().exists():
            missing.append(f"{markdown.relative_to(ROOT)} -> {target}")
assert not missing, "; ".join(missing)

hits = []
for item in manifest["files"]:
    path = ROOT / item["path"]
    if path.suffix.lower() in BINARY:
        continue
    value = path.read_text(encoding="utf-8")
    for name, pattern in SECRET_PATTERNS.items():
        if pattern.search(value):
            hits.append(f"{item['path']}:{name}")
assert not hits, "; ".join(hits)

report_pages = len(PdfReader(str(ROOT / "output/pdf/techflow-source-registry-report.pdf")).pages)
deck_pages = len(PdfReader(str(ROOT / "output/pdf/techflow-source-registry-presentation.pdf")).pages)
assert report_pages == 10, report_pages
assert deck_pages == 10, deck_pages
with zipfile.ZipFile(ROOT / "output/presentation/techflow-source-registry.pptx") as archive:
    slides = [name for name in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)]
    assert len(slides) == 10
    deck_text = "\n".join(archive.read(name).decode("utf-8", errors="ignore") for name in slides)
    for expected in ("ISSUE #42", "19 API", "PERSISTENT MIRRORS", "1,005 GiB", "ISSUE #43"):
        assert expected in deck_text, f"deck missing {expected}"

print(f"artifacts=valid files=45 links={checked_links} secrets=0 report_pages={report_pages} deck_pages={deck_pages} slides=10")
