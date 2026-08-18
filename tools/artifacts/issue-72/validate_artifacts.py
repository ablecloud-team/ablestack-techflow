#!/usr/bin/env python3
import json
from pathlib import Path
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[3]
EVIDENCE=ROOT/"docs/evidence/issue-72/large-upload-production-validation.json"
REPORT=ROOT/"output/pdf/techflow-issue-72-large-upload-report.pdf"
PRESENTATION=ROOT/"output/pdf/techflow-issue-72-large-upload-presentation.pdf"
PPTX=ROOT/"output/presentation/techflow-issue-72-large-upload.pptx"
MANIFEST=ROOT/"output/issue-72-large-upload-artifact-manifest.json"
data=json.loads(EVIDENCE.read_text(encoding="utf-8")); tests=data["tests"]
assert data["issue"]==72
assert data["policy"]["regularMaxBytes"]==1073741824
assert data["policy"]["archiveMaxBytes"]==10737418240
assert data["policy"]["extractedMaxBytes"]==107374182400
assert tests["runtimeRegression"]=={"total":263,"passed":263}
assert [item["status"] for item in tests["flarumBoundary"]]==[200,422,200,413]
assert [item["status"] for item in tests["gatewayBoundary"]]==[201,400,201,400]
assert tests["cleanup"]["flarumUploadRows"]==0 and tests["cleanup"]["temporaryFilesDeleted"] is True
assert all(item["result"]=="PASS" for item in tests["security"])
assert tests["protectedService"]["guard"]=="passed"
assert len(PdfReader(str(REPORT)).pages)>=7 and len(PdfReader(str(PRESENTATION)).pages)==6
assert PPTX.stat().st_size>25_000
manifest=json.loads(MANIFEST.read_text(encoding="utf-8")); assert manifest["issue"]==72 and manifest["artifactCount"]==len(manifest["artifacts"])
texts="\n".join((ROOT/p).read_text(encoding="utf-8") for p in ["docs/reports/issue-72-community-large-upload-validation.md","docs/runbooks/community-large-uploads.md"])
assert not any(token in texts for token in ["Ablecloud1!","Pdh1974","sk-proj-"])
print("Issue #72 artifacts: PASS")
