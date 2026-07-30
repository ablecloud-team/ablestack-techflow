# Issue #11 산출물 생성

Activepieces 기능·라이선스 검토 자료는 다음 순서로 일관되게 관리한다.

1. `docs/decisions/activepieces-license-review.json` — 판단의 단일 원본
2. `docs/decisions/activepieces-license-feature-matrix.md` — 사람이 검토하는 상세 문서
3. `output/pdf/activepieces-license-review-report.pdf` — 단계 확인·결재용 보고서
4. `output/presentation/activepieces-license-review.pptx` — 편집 가능한 발표 원본
5. `output/pdf/activepieces-license-review-presentation.pdf` — 발표 자료 보관본
6. `output/issue-11-artifact-manifest.json` — 버전·파일 SHA-256 증적

## 재생성

Windows PowerShell에서 저장소 루트를 기준으로 실행한다.

```powershell
powershell -ExecutionPolicy Bypass -File tools/artifacts/issue-11/build.ps1
```

프레젠테이션은 `@oai/artifact-tool`로 만들고, 보고서는 ReportLab으로 만든다. 중간 렌더링 파일과 설치된 생성 도구는 `tmp/` 아래에만 생성하며 Git에 커밋하지 않는다.

## 버전 갱신 절차

1. 분석할 Activepieces tag와 commit을 고정한다.
2. root·Enterprise 라이선스 파일의 SHA-256을 다시 계산한다.
3. 기능 분기와 라이선스 feature flag를 소스에서 재검토한다.
4. 공식 문서·Terms 변경일과 기능 설명을 확인한다.
5. JSON과 Markdown을 갱신한다.
6. `build.ps1`로 PDF·PPTX·manifest를 재생성한다.
7. 모든 PDF 페이지와 모든 슬라이드 렌더링을 시각 검수한다.
8. `git diff --check`와 파일 해시를 확인한다.

## 품질 기준

- 보고서와 프레젠테이션의 결론·버전·게이트가 JSON 원본과 일치한다.
- 고객 배포 권한을 추정으로 승인하지 않는다.
- 모든 비자명한 발표 주장에는 speaker notes의 `[Sources]` 블록이 있다.
- 슬라이드 겹침·오버플로 검사를 통과한다.
- PDF 글꼴과 한글이 깨지지 않는다.
- 비밀번호·토큰·개인정보를 포함하지 않는다.
