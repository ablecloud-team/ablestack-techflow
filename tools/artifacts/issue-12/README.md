# Issue #12 산출물 생성

TechFlow와 Activepieces 책임 경계 ADR 산출물은 다음 구조로 관리한다.

1. `docs/decisions/techflow-activepieces-responsibility-boundary.json`: 구조화된 단일 내용 원본
2. `docs/adr/0001-techflow-activepieces-responsibility-boundary.md`: 구현 규범 ADR
3. `output/pdf/techflow-responsibility-boundary-report.pdf`: 검토·승인용 보고서
4. `output/presentation/techflow-responsibility-boundary.pptx`: 편집 가능한 발표자료
5. `output/pdf/techflow-responsibility-boundary-presentation.pdf`: 발표자료 보관본
6. `output/issue-12-artifact-manifest.json`: 파일 크기와 SHA-256 증적

## 재생성

Windows PowerShell에서 저장소 루트를 기준으로 실행한다.

```powershell
powershell -ExecutionPolicy Bypass -File tools/artifacts/issue-12/build.ps1
```

보고서는 ReportLab으로 생성한다. 발표자료는 이슈 #11 PPTX를 시각 템플릿으로 사용하며 `@oai/artifact-tool`로 모든 소스 슬라이드를 검사하고 일대일 복제한 뒤 상속된 텍스트·표만 편집한다. 중간 파일은 `tmp/artifacts/issue-12/`에 생성한다.

## 변경 절차

1. 구조화된 JSON과 ADR을 함께 갱신한다.
2. README와 로드맵의 구현 규칙 참조를 확인한다.
3. `template-frame-map.json`의 슬라이드·요소 매핑을 유지한다.
4. `build.ps1`로 PDF·PPTX·매니페스트를 재생성한다.
5. 템플릿 충실도와 PPTX 넘침 검사를 통과시킨다.
6. 모든 PDF 페이지와 PPTX 슬라이드를 개별 시각 검수한다.
7. Markdown 링크, JSON, SHA-256과 비밀정보 검사를 수행한다.
8. `git diff --check`를 통과시킨다.

## 안전 기준

- FlowRun 성공을 실제 자원 성공으로 표현하지 않는다.
- Blind Retry를 허용하는 문구를 추가하지 않는다.
- 권한·정책·승인·감사와 최종 자원 상태의 소유자를 바꾸려면 ADR을 개정한다.
- 비밀번호, 토큰, API 키, 개인정보와 내부 로그 원문을 포함하지 않는다.
- 비자명한 발표 주장에는 speaker notes의 `[Sources]` 블록을 유지한다.
