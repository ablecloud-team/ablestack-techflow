#!/usr/bin/env python3
import json
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[3]
data = json.loads((ROOT / "docs/evidence/epic-4/production-e2e.json").read_text(encoding="utf-8"))
report = ROOT / "output/pdf/techflow-epic4-assist-validation-report.pdf"
slides = ROOT / "output/pdf/techflow-epic4-assist-validation-presentation.pdf"
pptx = ROOT / "output/presentation/techflow-epic4-assist-validation.pptx"
manifest = ROOT / "output/epic-4-assist-validation-artifact-manifest.json"

assert data["release"]["version"] == "0.15.0"
assert data["localValidation"]["testsPassed"] == 271
assert data["chatE2E"]["contextStateAfterResolve"] == "RESOLVED"
assert data["communityE2E"]["internalEvidenceExposed"] is False
assert data["continuityE2E"]["failureNotificationCount"] == 1
assert data["continuityE2E"]["recoveryNotificationCount"] == 1
assert data["continuityE2E"]["periodicSuccessNotificationCount"] == 0
assert all(item["unchanged"] for item in data["protectedServices"])
assert len(PdfReader(str(report)).pages) >= 6
assert len(PdfReader(str(slides)).pages) == 6
assert pptx.stat().st_size > 20_000
manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
assert manifest_data["epic"] == 4 and manifest_data["artifactCount"] == 7
texts = "\n".join(path.read_text(encoding="utf-8") for path in [
    ROOT / "docs/reports/epic4-assist-validation.md",
    ROOT / "docs/runbooks/epic4-service-continuity.md",
    ROOT / "docs/evidence/epic-4/production-e2e.json",
])
for marker in ["Able" + "cloud1!", "Pdh" + "1974", "sk-" + "proj-", "token=" + "%22"]:
    assert marker not in texts
print("Epic #4 artifacts: PASS")
