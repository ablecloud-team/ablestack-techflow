# Issue #42 산출물 빌드

Issue #42 구현·시험 서버 증적을 입력으로 보고서 PDF, 프레젠테이션 PPTX·PDF, SHA-256 Manifest를 재생성한다.

```powershell
powershell -ExecutionPolicy Bypass -File tools/artifacts/issue-42/build.ps1
```

프레젠테이션은 Codex Grid의 Cover, Metric, Timeline, Table, Closing 구성을 선별해 `@oai/artifact-tool`로 작성한다. 모든 Slide를 PNG로 Rendering하고 Overflow, 페이지 수, 링크, Secret, Checksum을 검증한다.

## 출력

- `output/pdf/techflow-source-registry-report.pdf`
- `output/presentation/techflow-source-registry.pptx`
- `output/pdf/techflow-source-registry-presentation.pdf`
- `output/issue-42-artifact-manifest.json`
