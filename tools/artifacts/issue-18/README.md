# Issue #18 산출물 빌드

Issue #18의 구조화 검증 JSON과 기존 TechFlow 프레젠테이션을 원본으로 보고서 PDF, 프레젠테이션 PPTX·PDF와 SHA-256 Manifest를 재생성한다.

```powershell
powershell -ExecutionPolicy Bypass -File tools/artifacts/issue-18/build.ps1
```

## 입력

- `docs/decisions/techflow-image-version-lock.json`
- `output/presentation/techflow-observability.pptx`
- `deploy/compose/activepieces/image-lock.json`

## 출력

- `output/pdf/techflow-image-version-lock-report.pdf`
- `output/presentation/techflow-image-version-lock.pptx`
- `output/pdf/techflow-image-version-lock-presentation.pdf`
- `output/issue-18-artifact-manifest.json`

빌드는 원본 10개 슬라이드 전체 검사, 동적 Frame Map과 Starter Deck 생성, 템플릿 충실도 검사, 보고서·슬라이드 렌더링과 Overflow 검사를 수행한다. 중간 파일은 `tmp/artifacts/issue-18`에만 생성한다.
