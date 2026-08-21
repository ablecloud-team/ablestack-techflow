# Issue #74 결과물 생성

## 생성 순서

```powershell
$env:RUNTIME_NODE_MODULES='C:\Users\ablecloud\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
$env:TECHFLOW_ROOT=(Get-Location).Path
node tools/artifacts/issue-74/build_presentation.mjs
python tools/artifacts/issue-74/build_report.py
python tools/artifacts/issue-74/build_presentation_pdf.py
python tools/artifacts/issue-74/build_manifest.py
python tools/artifacts/issue-74/validate_artifacts.py
```

PPTX는 Artifact Tool로 생성하며 PDF는 ReportLab과 검증된 Slide PNG를 사용한다. 생성 후 PDF Page 수, PPTX 크기, 구조화 증적, Secret 비포함과 Manifest SHA-256을 자동 검증한다.
