# Issue #41 산출물 빌드

Issue #41 AI Gateway 기반 코드·구조화 결정·Runbook을 입력으로 보고서 PDF, 프레젠테이션 PPTX·PDF와 SHA-256 Manifest를 재생성한다.

```powershell
powershell -ExecutionPolicy Bypass -File tools/artifacts/issue-41/build.ps1
```

## 출력

- `output/pdf/techflow-ai-gateway-foundation-report.pdf`
- `output/presentation/techflow-ai-gateway-foundation.pptx`
- `output/pdf/techflow-ai-gateway-foundation-presentation.pdf`
- `output/issue-41-artifact-manifest.json`

빌드는 기존 Issue #20 10장 자료를 시각 원본으로 사용하고, 전체 슬라이드 검사·1:1 Frame Map·Starter Deck·템플릿 충실도·Overflow·빈 Placeholder·PDF 페이지·링크·Secret Scan을 검증한다.
