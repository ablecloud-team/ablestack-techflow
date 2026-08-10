#!/usr/bin/env python3
"""Validate Issue #44 artifacts, pages, notes, manifest, and secret hygiene."""

import hashlib
import json
import re
import zipfile
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "output/issue-44-artifact-manifest.json"
BINARY = {".pdf", ".pptx"}
SECRET_PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github-token": re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    "openai-key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    "credential": re.compile(r"(?i)\b(?:password|api[_-]?key|api[_-]?secret)\s*[:=]\s*[\"'][^\"']{12,}[\"']"),
}


def canonical(path: Path) -> bytes:
    data = path.read_bytes()
    if path.suffix.lower() in BINARY:
        return data
    return data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
assert manifest["issue"] == 44
assert manifest["status"] == "implemented-deployed-and-validated"
assert len(manifest["files"]) == 32
for item in manifest["files"]:
    path = ROOT / item["path"]
    assert path.is_file(), item["path"]
    content = canonical(path)
    assert len(content) == item["size"], item["path"]
    assert hashlib.sha256(content).hexdigest().upper() == item["sha256"], item["path"]
    if path.suffix.lower() not in BINARY:
        value = content.decode("utf-8")
        for name, pattern in SECRET_PATTERNS.items():
            assert not pattern.search(value), f"{item['path']}:{name}"

assert len(PdfReader(str(ROOT / "output/pdf/techflow-grounded-responses-report.pdf")).pages) == 8
assert len(PdfReader(str(ROOT / "output/pdf/techflow-grounded-responses-presentation.pdf")).pages) == 10
with zipfile.ZipFile(ROOT / "output/presentation/techflow-grounded-responses.pptx") as archive:
    slides = [name for name in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)]
    assert len(slides) == 10
    slide_xml = "\n".join(archive.read(name).decode("utf-8", errors="ignore") for name in slides)
    for expected in ("ISSUE #44", "96 + 96", "보안심사", "Issue #45"):
        assert expected in slide_xml, expected
    notes = [name for name in archive.namelist() if re.fullmatch(r"ppt/notesSlides/notesSlide\d+\.xml", name)]
    assert len(notes) == 10
    for name in notes:
        assert "[Sources]" in archive.read(name).decode("utf-8", errors="ignore")

print(f"artifacts=valid files={len(manifest['files'])} secrets=0 reportPages=8 deckPages=10 slides=10 notes=10")
