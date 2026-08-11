#!/usr/bin/env python3
"""Validate the Issue #46 Golden Q&A, documents, PDFs, PPTX, and secrets."""

from __future__ import annotations

import json
from pathlib import Path
import re
import zipfile

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[3]
LIVE = ROOT / "output/issue-46-live-evaluation.json"
REPORT = ROOT / "docs/reports/issue-46-golden-set-quality-security-e2e-validation.md"
REPORT_PDF = ROOT / "output/pdf/techflow-golden-set-quality-security-e2e-report.pdf"
DECK = ROOT / "output/presentation/techflow-golden-set-quality-security-e2e.pptx"
DECK_PDF = ROOT / "output/pdf/techflow-golden-set-quality-security-e2e-presentation.pdf"
MANIFEST = ROOT / "output/issue-46-artifact-manifest.json"
SECRET_PATTERNS = [
    re.compile(rb"sk-proj-[A-Za-z0-9_-]{20,}"),
    re.compile(rb"api=SYNO\.Chat\.External[^\r\n]{0,300}token="),
    re.compile(rb"Pdh[0-9]{4}[!@#]"),
    re.compile(rb"Ablecloud[0-9]+!"),
]


data = json.loads(LIVE.read_text(encoding="utf-8"))
records = data["records"]
assert data["executionMode"] == "LIVE_GATEWAY"
assert len(records) >= 50
assert all(item.get("question") for item in records)
assert all("actualAnswer" in item for item in records)
assert all(item.get("reviewJudgment", {}).get("reviewer") == "Codex" for item in records)
assert all(item.get("reviewJudgment", {}).get("verdict") in {"ACCEPTED", "REJECTED"} for item in records)
report_text = REPORT.read_text(encoding="utf-8")
assert all(item["caseKey"] in report_text and item["question"] in report_text for item in records)

report_pages = len(PdfReader(str(REPORT_PDF)).pages)
deck_pages = len(PdfReader(str(DECK_PDF)).pages)
assert report_pages >= 10
assert deck_pages == 10
with zipfile.ZipFile(DECK) as archive:
    slides = [name for name in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)]
    notes = [name for name in archive.namelist() if re.fullmatch(r"ppt/notesSlides/notesSlide\d+\.xml", name)]
    assert len(slides) == 10
    assert len(notes) == 10
    note_text = b"\n".join(archive.read(name) for name in notes)
    assert note_text.count(b"[Sources]") == 10

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
assert manifest["artifactCount"] >= 14
for item in manifest["artifacts"]:
    body = (ROOT / item["path"]).read_bytes()
    assert not any(pattern.search(body) for pattern in SECRET_PATTERNS), item["path"]

print(json.dumps({
    "valid": True,
    "goldenQuestions": len(records),
    "reviewJudgments": len(records),
    "reportPages": report_pages,
    "presentationSlides": len(slides),
    "presentationPdfPages": deck_pages,
    "artifactCount": manifest["artifactCount"],
    "secretPatternMatches": 0,
}, ensure_ascii=False))
