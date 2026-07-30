# Issue #13 산출물 생성

Activepieces Compose 배포 결과와 서버 배포 절차는 다음 구조로 관리한다.

1. `docs/decisions/activepieces-compose-deployment.json`: 구조화된 검증 단일 원본
2. `deploy/compose/activepieces/`: Compose, 환경 계약, 설치·배포·검증 스크립트
3. `docs/runbooks/activepieces-compose-deployment.md`: 설치부터 장애 대응·제거까지의 운영 Runbook
4. `docs/reports/issue-13-activepieces-compose-deployment-validation.md`: Markdown 검증 보고서
5. `output/pdf/activepieces-compose-deployment-report.pdf`: 검토·보관용 보고서
6. `output/presentation/activepieces-compose-deployment.pptx`: 편집 가능한 발표자료
7. `output/pdf/activepieces-compose-deployment-presentation.pdf`: 발표자료 보관본
8. `output/issue-13-artifact-manifest.json`: 배포·문서·보고 자산의 파일 크기와 SHA-256 증적

## 재생성

Windows PowerShell에서 저장소 루트를 기준으로 실행한다.

```powershell
powershell -ExecutionPolicy Bypass -File tools/artifacts/issue-13/build.ps1
```

보고서는 ReportLab으로 생성한다. 발표자료는 이슈 #11 PPTX를 공통 시각 템플릿으로 사용하며 `@oai/artifact-tool`로 모든 소스 슬라이드를 검사하고 일대일 복제한 뒤 상속된 텍스트·표만 편집한다. 중간 파일은 `tmp/artifacts/issue-13/`에 생성한다.

## 변경 절차

1. Compose·스크립트·Runbook을 변경한다.
2. 실서버에 동일한 파일을 배포하고 Health·영속성·재부팅 복구를 검증한다.
3. 구조화된 JSON과 Markdown 검증 보고서를 갱신한다.
4. `template-frame-map.json`의 슬라이드·요소 매핑을 유지한다.
5. `build.ps1`로 PDF·PPTX·매니페스트를 재생성한다.
6. 템플릿 충실도와 PPTX 넘침 검사를 통과시킨다.
7. 모든 PDF 페이지와 PPTX 슬라이드를 개별 시각 검수한다.
8. Markdown 링크, JSON, SHA-256과 비밀정보 검사를 수행한다.
9. `git diff --check`를 통과시킨다.

## 안전 기준

- `.env`, SSH 비밀번호, API 키, 토큰, 암호화 키와 내부 로그 원문을 포함하지 않는다.
- 데이터 볼륨 제거는 명시적인 확인 변수 없이는 실행하지 않는다.
- Worker의 컨테이너 Health뿐 아니라 Polling 준비 상태까지 검증한다.
- 서버 재부팅 후 Docker·컨테이너·HTTP·Worker 복구를 확인한다.
- 비자명한 발표 주장에는 speaker notes의 `[Sources]` 블록을 유지한다.
