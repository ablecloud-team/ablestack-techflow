#!/usr/bin/env python3
"""Validate Issue #71 documents and binary deliverables."""

from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "docs/evidence/issue-71/flarum-1.8.18-validation.json"
REPORT = ROOT / "output/pdf/techflow-flarum-1.8.18-upgrade-report.pdf"
PRESENTATION_PDF = ROOT / "output/pdf/techflow-flarum-1.8.18-upgrade-presentation.pdf"
PPTX = ROOT / "output/presentation/techflow-flarum-1.8.18-upgrade.pptx"
MANIFEST = ROOT / "output/issue-71-flarum-upgrade-artifact-manifest.json"

data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
assert data["decision"] == "CONDITIONAL_GO"
assert data["production_changed"] is False
assert data["staging"]["final_core"] == "1.8.18"
assert len(data["repeatable_cycles"]) >= 2
assert all(item["upgrade"] == "PASS" and item["rollback"] == "PASS" for item in data["repeatable_cycles"])
assert data["integrity"]["rollback_business_data_equal"] is True
assert data["functional_validation"]["korean_raw_translation_keys"] == 0
assert data["functional_validation"]["techflow_unittest_count"] == 216
assert len(PdfReader(str(REPORT)).pages) >= 7
assert len(PdfReader(str(PRESENTATION_PDF)).pages) == 7
assert PPTX.stat().st_size > 30_000
manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
assert manifest["issue"] == 71
assert manifest["artifactCount"] == len(manifest["artifacts"])
assert not any(token in (ROOT / "docs/reports/issue-71-flarum-1.8.18-validation.md").read_text(encoding="utf-8") for token in ["Ablecloud1!", "Pdh1974", "sk-proj-"])
print("Issue #71 artifacts: PASS")
