# Diplo 현재판·Europa 프리뷰 안전 답변 배포·운영 Runbook

## 배포 전

1. `main...upstream/main`이 `0 0`인지 확인한다.
2. 전체 AI Gateway 단위 시험과 OpenAPI 생성을 수행한다.
3. `protected_service_guard.py`로 `github-chat-v1 state=frozen guard=passed`를 확인한다.
4. 시험 서버 `/` 용량과 AI Gateway·Community Poller 상태를 확인한다.
5. `services/ai-gateway`, Compose 설정, 현재 Gateway Image Inspect를 UTC 시각 백업 경로에 복사한다.

## 배포

시험 서버 작업 루트는 `/home/ablecloud/techflow-ai-gateway`다. Secret 파일과 `.env`는 기존 서버 파일을 그대로 사용하고 배포 묶음에 포함하지 않는다.

```bash
cd /home/ablecloud/techflow-ai-gateway/deploy/compose/ai-gateway
export TECHFLOW_RAG_RELEASE=issue-63-troubleshooting
docker compose --env-file .env \
  -f compose.yml -f compose.openai.override.yml \
  build gateway community-poller
docker compose --env-file .env \
  -f compose.yml -f compose.openai.override.yml \
  up -d gateway community-poller
```

## 확인

1. `/healthz`에서 Version `0.11.3`, Database·Vector `ready`, Provider `openai`를 확인한다.
2. 일반 Assist 질문이 Coverage 9개와 현재판·플랫폼 런타임·프리뷰 구조화 판정을 반환하는지 확인한다.
3. 일반 Chat 사용자의 기술 질문이 Reviewer 권한 없이 응답되며 내부 계보가 없는지 확인한다.
4. Community 질문이 `DRAFT_PENDING` Case를 생성하고 `ANSWERED` 또는 올바른 보류 판정을 갖는지 확인한다.
5. 승인 담당자의 Chat `상세 <Case>`에는 답변만 표시되고, `근거 <Case>`에서만 내부 Citation, 전체 Coverage, 현재판·프리뷰 판정이 표시되는지 확인한다.
6. Community 공개 Draft에서 `github.com`, Source Profile, 저장소, Commit, 경로, 라인 패턴이 0건인지 확인한다.
7. `techflow-activepieces-event-gateway-1`이 재시작 없이 기존 Image로 계속 `healthy`인지 확인한다.
8. 일반 Chat과 Community Draft에 `증상`, `원인`, `해결 방법`, `추가 고려사항`, `적용 버전`이 순서대로 모두 나타나는지 확인한다.
9. 신규 Discussion 생성 후 Poll 10초와 AI 생성 시간 내 Reviewer에게 Chat 알림이 도착하고, 알림·`상세`에는 근거가 없으며 `근거 <Case>`에서만 Ledger가 보이는지 확인한다.

HTTP 200만으로 성공 판정하지 않는다. 구조화 상태, Coverage, 외부 Projection 검사, Reviewer Ledger, 컨테이너 Health를 모두 확인한다.

## 운영 판정

- 범용 장애 질문이 특정 환경·로그 없이 입력되면 `INSUFFICIENT_EVIDENCE`로 보류하는 것이 정상이다.
- 코드 식별자나 재현 정보가 충분하면 관련 Profile 근거만 생성 컨텍스트에 포함한다.
- Europa에 동일 클래스가 존재하는 것만으로 개선으로 판정하지 않는다. 동일 원인에 대한 변경 근거가 있어야 한다.
- `PREVIEW_NOT_FOUND`는 향후 보완 검토 가이드이며 출시 계획을 대신하지 않는다.
- `적용 버전`에는 Diplo 현재 출시판과 Europa 미출시 Preview를 분리해 표시하며, 근거 없는 숫자 버전과 출시 일정을 생성하지 않는다.
- QEMU/libvirt 참조는 승인된 로컬 스냅샷만 사용한다. 30일 주기 변경 확인 후 Source Reviewer 승인으로만 활성화한다.
- 콘솔 `연결중` 단일 VM 사례는 `CURRENT_RUNTIME_ISSUE`로 분류한다. 읽기 전용 진단은 `virsh domstate`, `virsh domdisplay`, QMP `query-vnc`, `virsh dumpxml`, `journalctl` 순으로 수행한다.
- 운영 VM 조치는 Mold의 라이브 마이그레이션을 우선하고, 불가능하면 서비스 중단을 고지한 뒤 정지 후 시작한다. 직접 `virsh migrate`는 승인된 예외 절차가 아니면 실행하지 않는다.

## 롤백

1. Gateway와 Community Poller만 이전 Image Tag로 되돌린다.
2. 필요하면 `/home/ablecloud/techflow-ai-gateway-backups/issue62-predeploy-<UTC>`의 소스와 Compose를 복원한다.
3. Database Migration은 추가되지 않았으므로 Schema 롤백은 필요 없다.
4. Community에 이미 게시된 답변은 자동 삭제하지 않는다.
5. 테스트용 Discussion도 자동 삭제하지 않고 E2E 증적으로 유지한다.
6. `github-chat-v1`과 Event Gateway는 롤백 대상에 포함하지 않는다.

## Secret 정책

SSH 암호, OpenAI Key·Project ID, Flarum API Key, Chat Bot Token, Activepieces Webhook URL은 서버의 기존 보호 파일 또는 실행 환경에서만 사용한다. 명령 출력·보고서·Git 저장소·배포 묶음에 값을 남기지 않는다.
