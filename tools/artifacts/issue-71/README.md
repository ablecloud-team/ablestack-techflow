# Issue #71 산출물 빌드

## 결과물

- `output/pdf/techflow-flarum-1.8.18-upgrade-report.pdf`
- `output/presentation/techflow-flarum-1.8.18-upgrade.pptx`
- `output/pdf/techflow-flarum-1.8.18-upgrade-presentation.pdf`
- `output/issue-71-flarum-upgrade-artifact-manifest.json`

## 빌드

Codex 번들 Python/Node 경로를 명시한 뒤 실행한다.

```powershell
python tools/artifacts/issue-71/build_report.py
node tools/artifacts/issue-71/build_presentation.mjs <repository-root>
python tools/artifacts/issue-71/build_presentation_pdf.py
python tools/artifacts/issue-71/build_manifest.py
python tools/artifacts/issue-71/validate_artifacts.py
```

PPTX 빌더는 `@oai/artifact-tool`을 사용하며, 빌드 디렉터리의 `node_modules`는 Codex 번들 모듈 경로를 가리켜야 한다.
