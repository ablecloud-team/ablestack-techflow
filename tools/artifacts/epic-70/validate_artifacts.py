#!/usr/bin/env python3
import json
from pathlib import Path
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[3]
data = json.loads((ROOT / "docs/evidence/epic-70/community-modernization-e2e.json").read_text(encoding="utf-8"))
report = ROOT / "output/pdf/techflow-community-modernization-report.pdf"
slides = ROOT / "output/pdf/techflow-community-modernization-presentation.pdf"
pptx = ROOT / "output/presentation/techflow-community-modernization.pptx"
manifest = ROOT / "output/epic-70-community-modernization-artifact-manifest.json"

assert data["epic"] == 70 and data["decision"] == "GO"
assert data["repositoryValidation"]["aiGatewayTests"]["passed"] == 153
assert data["repositoryValidation"]["communityThemeAndOperationsTests"]["passed"] == 22
e2e = data["operationalE2E"]
assert e2e["conversationState"] == "RESOLVED"
assert e2e["knowledgeBasePostId"] == e2e["finalBestAnswerPostId"] == "408"
assert len(e2e["attachments"]) == 2 and all(item["synthetic"] for item in e2e["attachments"])
assert data["protectedService"]["changed"] is False
assert data["protectedService"]["guardBefore"] == data["protectedService"]["guardAfter"] == "passed"
assert len(PdfReader(str(report)).pages) >= 6
assert len(PdfReader(str(slides)).pages) == 6
assert pptx.stat().st_size > 25_000
manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
assert manifest_data["epic"] == 70 and manifest_data["artifactCount"] == 8
texts = "\n".join(path.read_text(encoding="utf-8") for path in [
    ROOT / "docs/reports/epic-70-community-modernization-validation.md",
    ROOT / "docs/runbooks/community-platform-integrated-e2e.md",
    ROOT / "docs/evidence/epic-70/community-modernization-e2e.json",
])
for marker in ["Able" + "cloud1!", "Pdh" + "1974", "sk-" + "proj-", "token=" + "%22"]:
    assert marker not in texts
print("Epic #70 artifacts: PASS")
