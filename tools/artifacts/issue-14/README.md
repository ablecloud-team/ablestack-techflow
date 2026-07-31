# Issue #14 산출물 빌드

Issue #14의 검증 JSON과 기존 TechFlow 프레젠테이션을 원본으로 보고서 PDF, 프레젠테이션 PPTX·PDF와 SHA-256 Manifest를 재생성한다.

```powershell
powershell -ExecutionPolicy Bypass -File tools/artifacts/issue-14/build.ps1
```

## 입력

- `docs/decisions/https-webhook-ingress.json`
- `output/presentation/activepieces-compose-deployment.pptx`
- `tools/artifacts/issue-14/template-frame-map.json`

## 출력

- `output/pdf/https-webhook-ingress-report.pdf`
- `output/presentation/https-webhook-ingress.pptx`
- `output/pdf/https-webhook-ingress-presentation.pdf`
- `output/issue-14-artifact-manifest.json`

빌드는 템플릿 검사, Starter Deck 생성, 프레임 충실도 검사, 슬라이드 렌더링과 Overflow 검사를 수행한다. 중간 파일은 `tmp/artifacts/issue-14`에 생성하며 커밋하지 않는다.
