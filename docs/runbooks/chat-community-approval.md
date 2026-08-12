# Chat 기반 Community 승인 배포·운영 Runbook

## 1. 보호 경계

배포 전후 다음 보호 가드를 실행한다.

```bash
python deploy/compose/activepieces/scripts/protected_service_guard.py \
  --lock deploy/compose/activepieces/protected-services.json \
  --env-file deploy/compose/activepieces/.env.example \
  --compose deploy/compose/activepieces/compose.yml \
  --ingress deploy/compose/activepieces/ingress/Caddyfile
```

결과는 `protected_service=github-chat-v1 state=frozen guard=passed`여야 한다. 기존 `/techflow/hooks/*`, GitHub Flow, Event Gateway와 Chat Adapter는 변경·재배포하지 않는다.

## 2. Secret과 설정

GitHub Actions Secret은 다음 이름을 사용한다.

- `TECHFLOW_CHAT_BOT_TOKEN`
- `TECHFLOW_FLARUM_API_KEY`
- `TECHFLOW_COMMUNITY_APPROVE_WEBHOOK_URL`
- `TECHFLOW_COMMUNITY_REJECT_WEBHOOK_URL`

서버에서는 실제 값을 `.secrets`의 보호 파일로만 두고 Compose에는 파일 참조를 전달한다.

```text
TECHFLOW_CHAT_BOT_ENABLED=true
TECHFLOW_CHAT_BASE_URL=https://chat.ablecloud.io
TECHFLOW_CHAT_BOT_TOKEN_SECRET_FILE=/protected/path/chat-bot-token
TECHFLOW_CHAT_REVIEWER_USERNAMES=<허용된 사용자 이름 목록>
TECHFLOW_COMMUNITY_APPROVE_WEBHOOK_SECRET_FILE=/protected/path/community-approve-webhook
TECHFLOW_COMMUNITY_REJECT_WEBHOOK_SECRET_FILE=/protected/path/community-reject-webhook
```

Flarum 서버 간 전송은 시험망의 사설 경로 `http://172.16.0.234`, 사용자에게 보여 주는 링크는 `https://community.ablecloud.io`로 분리한다. Token, Webhook URL, API Key, 비밀번호와 인증 응답은 로그·문서·Git에 기록하지 않는다.

## 3. Synology Chat Bot 설정

1. Chat 관리 화면에서 Bot 이름과 설명을 생성한다.
2. Outgoing URL을 `https://techflow.ablecloud.io/techflow/chat/assist`로 설정한다.
3. 생성된 Token을 GitHub Secret과 서버 보호 파일에 주입한다.
4. 담당자는 Bot 대화에서 `연결`을 한 번 실행한다.
5. `대기`, `상세`, `이력`으로 연결과 권한을 확인한다.

Bot Token은 URL·문서에 직접 복사하지 않는다. Synology Chat의 outgoing/interactive callback 필드와 incoming Bot 메시지·버튼 계약을 사용한다.

## 4. 사전 백업

시험 서버 배포 전 다음을 `/home/ablecloud/techflow-ai-gateway/backups/issue22-predeploy-<UTC>`에 저장한다.

- AI Gateway PostgreSQL Custom Dump
- AI Gateway와 Activepieces Compose
- Caddy Ingress 설정
- 직전 Gateway Image ID
- 배포 대상 Source
- `SHA256SUMS`

배포 전에 `sha256sum -c SHA256SUMS`를 실행하고, 백업 디렉터리와 파일 권한이 운영 기준을 충족하는지 확인한다.

## 5. 배포 절차

1. 새 Gateway 이미지를 `techflow/ai-gateway:issue-22-chat-approval`로 빌드한다.
2. `0009_chat_approval_up.sql`을 적용한다.
3. Schema가 22개 Table이고 `chat_reviewer_identity`가 존재하는지 확인한다.
4. AI Gateway를 Activepieces `automation` Network의 고정 주소 `172.30.19.3`으로 기동한다.
5. Community Poller는 충돌을 피하도록 `172.30.19.4`로 고정한다.
6. Caddy Ingress를 `automation_egress` Network에 추가하고 Chat 전용 Route를 적용한다.
7. Gateway와 Poller만 재생성한다. GitHub Chat 보호 서비스는 건드리지 않는다.
8. Health, 외부 위조 요청 403, Chat 연결·대기·이력을 확인한다.

```bash
curl -fsS http://127.0.0.1:18090/healthz
curl -sS -o /dev/null -w '%{http_code}' \
  -X POST https://techflow.ablecloud.io/techflow/chat/assist \
  -d 'token=invalid&text=help'
```

두 번째 명령은 `403`이어야 한다.

## 6. 담당자 운영 절차

1. `대기`로 검토 대상 Case를 찾는다.
2. `상세 <Case>` 또는 알림 버튼으로 질문, AI 판정, 초안과 Citation을 확인한다.
3. 초안이 그대로 적합하면 `승인 <Case> <Version>`을 실행한다.
4. 수정이 필요하면 `수정 <Case> <Version> <최종 답변>`을 실행한다.
5. 근거가 부족하거나 부적합하면 `반려 <Case> <Version> <사유>`를 실행한다.
6. `이력` 또는 `이력 <Case>`로 최종 상태와 Reviewer를 확인한다.

Chat에 표시된 최종 상태가 `PUBLISHED`인 경우에만 Community 게시 완료로 판정한다. 단순 Webhook HTTP 200은 성공 판정 기준이 아니다.

## 7. 영구 삭제된 원본 정리

원본 Discussion이 영구 삭제되면 게시를 재시도하지 않는다. 운영자는 삭제 사실을 확인한 뒤 Case를 `REJECTED`로 전환하고 Reviewer를 `techflow:source-deletion-reconcile`로 기록한다. 감사 Event에는 Discussion ID, 확인 시각과 사유를 남기되 삭제된 원문을 복원하거나 저장하지 않는다.

Discussion #143은 이 절차로 정리했다. 이후 `대기`에서 제외되고 `이력`에 삭제 정리 Reviewer가 표시되는지 확인했다.

## 8. 롤백

1. `TECHFLOW_CHAT_BOT_ENABLED=false`로 Chat 경로를 Fail-closed 처리한다.
2. Gateway Image와 Compose를 사전 백업본으로 복구한다.
3. Caddy의 `/techflow/chat/assist` 블록과 Gateway Network 연결만 되돌린다.
4. 기존 `/techflow/hooks/*`, Event Gateway, GitHub Chat Flow는 그대로 유지한다.
5. Migration Down은 Reviewer 연결 이력을 삭제하므로 제품 책임자의 명시적 승인과 DB Dump 검증 후에만 실행한다.
6. 이미 게시된 Community 답변은 자동 삭제하지 않는다.

## 9. 점검 명령

```bash
docker ps --format '{{.Names}}|{{.Image}}|{{.Status}}'
docker run --rm --user 0:0 \
  -v /home/ablecloud/techflow-ai-gateway:/workspace:ro \
  -w /workspace/services/ai-gateway \
  --entrypoint python techflow/ai-gateway:issue-22-chat-approval \
  -m unittest discover -s tests -p 'test_*.py'
docker exec techflow-ai-gateway-database-1 \
  psql -U techflow_bootstrap -d techflow_rag -Atc \
  "select count(*) from pg_catalog.pg_tables where schemaname='public';"
```
