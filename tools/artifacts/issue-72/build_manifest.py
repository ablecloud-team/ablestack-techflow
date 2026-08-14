#!/usr/bin/env python3
from datetime import datetime, timezone
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUTPUT=ROOT/"output/issue-72-large-upload-artifact-manifest.json"
ARTIFACTS=[
 "deploy/flarum/issue72-large-upload-policy.sh","docs/evidence/issue-72/large-upload-production-validation.json",
 "docs/runbooks/community-large-uploads.md","docs/reports/issue-72-community-large-upload-validation.md",
 "output/pdf/techflow-issue-72-large-upload-report.pdf","output/presentation/techflow-issue-72-large-upload.pptx",
 "output/pdf/techflow-issue-72-large-upload-presentation.pdf","tools/artifacts/issue-72/README.md",
 "tools/artifacts/issue-72/build_report.py","tools/artifacts/issue-72/build_presentation.mjs",
 "tools/artifacts/issue-72/build_presentation_pdf.py","tools/artifacts/issue-72/build_manifest.py","tools/artifacts/issue-72/validate_artifacts.py"]
items=[]
for relative in ARTIFACTS:
    path=ROOT/relative
    if not path.is_file(): raise SystemExit(f"missing artifact: {relative}")
    body=path.read_bytes(); items.append({"path":relative,"bytes":len(body),"sha256":hashlib.sha256(body).hexdigest()})
OUTPUT.write_text(json.dumps({"schemaVersion":"1.0","issue":72,"generatedAt":datetime.now(timezone.utc).isoformat(),"artifactCount":len(items),"artifacts":items},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(OUTPUT)

