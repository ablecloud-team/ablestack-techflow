# Issue #16 산출물 빌드

Issue #16의 백업·복구 검증 JSON과 기존 TechFlow 프레젠테이션을 원본으로 보고서 PDF, 프레젠테이션 PPTX·PDF와 SHA-256 Manifest를 재생성한다.

```powershell
powershell -ExecutionPolicy Bypass -File tools/artifacts/issue-16/build.ps1
```

## 입력

- `docs/decisions/techflow-state-backup-recovery.json`
- `output/presentation/techflow-secret-management.pptx`
- `tools/artifacts/issue-16/template-frame-map.json`

## 출력

- `output/pdf/techflow-backup-recovery-report.pdf`
- `output/presentation/techflow-backup-recovery.pptx`
- `output/pdf/techflow-backup-recovery-presentation.pdf`
- `output/issue-16-artifact-manifest.json`

빌드는 10개 원본 슬라이드 전체 검사, Starter Deck 생성, 프레임 충실도 검사, 보고서·슬라이드 렌더링과 Overflow 검사를 수행한다. 중간 파일은 `tmp/artifacts/issue-16`에 생성하며 커밋하지 않는다.

Manifest는 PDF·PPTX의 원본 바이트를 해시하고 UTF-8 텍스트는 LF로 정규화한 뒤 해시한다. 따라서 Windows CRLF와 Linux LF 작업 트리에서 동일한 체크섬을 유지한다.
