# Discussion #186 처리 점검과 초기 답변 검토

2026-09-18 확인. Issue #120 / PR #121.

## 발견 사항

- Gateway/Poller는 7일간 Healthy였지만, 답변 실행 안내 검사에서 Windows 이벤트 로그에 Linux SSH·서비스·로그 경로를 요구해 503으로 게시가 거절됐다.
- FoF 첨부 다운로드 경로가 실패하여 이미지 하나만 Artifact로 들어갔다. 동일 AI 계정으로 접근 가능한 파일 메타데이터에서 UUID를 대조하면 실제 저장 주소를 확인할 수 있다.
- 0918.zip 다운로드 크기는 926,602,290바이트이고 중앙 디렉터리에 714개 항목, 선언된 해제 크기 11,636,123,661바이트가 있다. 내부 로그의 암호화 플래그를 확인했으며 내용은 읽지 않았다.
- 자동 재처리에서는 외부 자료 조회가 PROVIDER_INVALID_RESPONSE로 실패했다. 전체 AI 자동 응답이 정상이라고 단정하지 않는다.

## 배포한 수정

- Windows 로그만 안내하는 답변에 Linux 전용 조건을 적용하지 않는다.
- `journalctl -k`는 커널 로그이므로 `.service`를 요구하지 않는다. 실제 서비스 조회 검사 조건은 유지한다.
- 동일 파일 UUID, 기존 AI 계정 권한, 신뢰하는 사이트의 `/assets/files/` 경로만 사용해 첨부 주소를 해석한다.
- 암호화 ZIP을 식별하고 공개 댓글에 암호를 요청하지 않는 구체적 사유를 기록한다.
- 운영 이미지 `techflow/ai-gateway:discussion186-fa5ab6b`. Gateway/Poller만 교체했다. 둘 다 Healthy, Restart 0이며 보호 서비스 ID는 동일했다. Community·Chat HTTP 200.

## 검토한 초기 답변

이미지에는 Windows Server 2022 VM, 9월 18일 04:31:29 BACKUP.CREATE 시작, 전날 admin 계정의 VM.STOP/START가 표시된다. 캡처 당시 Running을 장애 순간의 정상 상태로 보거나 전날 수동 종료를 새벽 자동 종료 원인으로 해석하지 않았다.

Diplo 소스 `10973eeb4d284e2d35c1004b2b3f92e8208f0fd1`의 `LibvirtTakeBackupCommandWrapper`와 `nasbackup.sh`에서 NAS 백업의 선택적 guest-fsfreeze-freeze / backup-begin / guest-fsfreeze-thaw 순서를 확인했다. 실제 백업 공급자가 확인되지 않았으므로 이 분기를 원인으로 단정하지 않았다.

Microsoft 공식 Windows 재시작 진단 문서에 근거해 이벤트 1074·41·6008과 BugCheck 관련 1001의 의미를 설명했다. VM 전원 종료와 게스트 응답 멈춤을 구분하고, RDP 또는 Mold 콘솔 접속 후 관리자 PowerShell에서 시각을 한정한 System 이벤트 조회를 안내했다.

자동 생성 실패 후 검토한 초기 답변을 TechFlow-Assistant Post #480으로 게시했다. Case `340cd3d1-fe53-4f62-9e33-ccdc7a50bd03`에 질문·이미지 Artifact·암호화 경고·답변을 함께 기록했다. 브라우저에서 게시와 코드 블록을 확인했다. 원인 분석은 암호 확인 대기이며 해결 처리하지 않았다.

## 검증 범위와 잔여 작업

- 운영 이미지의 conversation/poller/community 통합시험 112건 통과.
- Windows 로컬 전체 시험은 누락된 개발 의존성과 비추적 tmp 연구 파일의 CRLF 검사 실패가 있어 통과로 보고하지 않는다.
- ZIP 암호가 없으므로 로그 내용 분석과 실제 장애 원인 판정은 아직 수행하지 못했다.
- 암호화 첨부 전용 대기 상태, 관리자 Chat 일회성 알림, 관리자용 비밀 제출 API/CLI, 자동 복호화 후 재개는 설계 단계다. 일반 Chat에 암호를 보내면 대화 DB와 AI 입력에 포함될 수 있어 이 경로를 사용하지 않는다.
- 채택한 절차: 관리자 Chat 알림 → 관리자가 게시자에게 암호 확보 → 엔진 일회성 전달 → 제한된 복호화·비밀 폐기 → 같은 Case 재개. 게시자와 Chat 사용자 계정 연결은 필요하지 않다.

절차: [암호화 지원 첨부 처리](../plans/encrypted-support-artifact-workflow.md).

근거: https://learn.microsoft.com/en-us/troubleshoot/windows-server/performance/troubleshoot-unexpected-reboots-system-event-logs
