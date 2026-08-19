#!/usr/bin/env python3
import json
from pathlib import Path
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "docs/evidence/issue-74/community-operations-validation.json"
REPORT = ROOT / "output/pdf/techflow-community-operations-report.pdf"
PRESENTATION = ROOT / "output/pdf/techflow-community-operations-presentation.pdf"
PPTX = ROOT / "output/presentation/techflow-community-operations.pptx"
MANIFEST = ROOT / "output/issue-74-community-operations-artifact-manifest.json"

data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
assert data["issue"] == 74 and data["result"] == "GO"
assert data["backup"]["integrity"] == "PASS"
assert data["backup"]["productionPrivateKeyPresent"] is False
assert data["restore"]["rtoSeconds"] == 9 and data["restore"]["httpStatus"] == 200
assert data["restore"]["plaintextAppRemoved"] is True and data["restore"]["temporaryDatabaseRemoved"] is True
assert all(item["source"] == item["restored"] for item in data["restore"]["counts"].values())
assert data["monitoring"]["activeAlerts"] == 0 and data["monitoring"]["productionChatHttp"] == 200
assert data["security"]["rateLimit429"] > 0
assert data["security"]["secretScanFindings"] == 0 and data["security"]["worldWritableFiles"] == 0
assert len(PdfReader(str(REPORT)).pages) >= 7
assert len(PdfReader(str(PRESENTATION)).pages) == 10
assert PPTX.stat().st_size > 25_000
manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
assert manifest["issue"] == 74 and manifest["artifactCount"] == len(manifest["artifacts"])
texts = "\n".join(path.read_text(encoding="utf-8") for path in [
    ROOT / "docs/reports/issue-74-community-operations-validation.md",
    ROOT / "docs/runbooks/community-backup-monitor-security.md",
    ROOT / "docs/adr/0010-community-backup-observability-security.md",
])
sensitive_markers = [
    "Able" + "cloud1!",
    "Pdh" + "1974",
    "sk-" + "proj-",
    "token=" + "%22",
]
assert not any(token in texts for token in sensitive_markers)
print("Issue #74 artifacts: PASS")
