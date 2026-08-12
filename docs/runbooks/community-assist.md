# Community Assist 배포·운영 Runbook

## 1. 보호 경계

배포 전후 `protected_service_guard.py`가 `github-chat-v1 state=frozen guard=passed`를 반환해야 한다. Issue #21은 AI Gateway, Community Poller와 새 Community Flow 3개만 변경한다.

## 2. Secret

GitHub Actions Secret은 다음 이름을 사용한다.

- `TECHFLOW_FLARUM_SSH_HOST`, `TECHFLOW_FLARUM_SSH_PORT`, `TECHFLOW_FLARUM_SSH_USER`, `TECHFLOW_FLARUM_SSH_PASSWORD`
- `TECHFLOW_FLARUM_BASE_URL`, `TECHFLOW_FLARUM_ADMIN_USER`, `TECHFLOW_FLARUM_ADMIN_PASSWORD`
- `TECHFLOW_FLARUM_API_KEY`
- `TECHFLOW_COMMUNITY_INGEST_WEBHOOK_URL`, `TECHFLOW_COMMUNITY_APPROVE_WEBHOOK_URL`, `TECHFLOW_COMMUNITY_REJECT_WEBHOOK_URL`

실제 값은 출력하거나 저장소 파일에 쓰지 않는다. 시험 서버에서는 상위 `.secrets` 디렉터리를 `0700`으로 제한하고 컨테이너 비루트 UID가 읽어야 하는 Secret 파일만 `0644`로 bind mount한다.

시험망은 공인 주소에 대한 NAT hairpin이 되지 않으므로 Flarum 전송 경로와 사용자 공개 URL을 분리한다.

- `TECHFLOW_FLARUM_BASE_URL=http://172.16.0.234`: 서버 간 사설망 JSON:API 전송 전용
- `TECHFLOW_FLARUM_PUBLIC_URL=https://community.ablecloud.io`: Case, 첨부 검증, 게시 결과 링크 전용

두 값은 코드의 고정 allowlist 밖 주소를 거부한다. 첨부 링크는 공개 HTTPS same-origin을 먼저 검증한 뒤 동일 path와 query만 내부 API 주소로 변환해 가져온다.

## 3. Flarum 백업

Flarum 변경 전 DB Dump, `config.php`·Composer Lock과 Nginx 구성을 `/var/backups/ablestack-techflow/flarum-issue21-<UTC>`에 `root:root 0700/0600`으로 보관하고 `SHA256SUMS`를 검증한다.

## 4. Flow 배포

`community-assist-v1.json`을 `manage-rag-flows.py`로 게시한다. 예상 Flow는 다음 세 개다.

1. `TechFlow - Community Question Draft v1`
2. `TechFlow - Community Approve and Publish v1`
3. `TechFlow - Community Reject Draft v1`

모두 `security.automaticApproval=false`여야 한다. 외부 Caddy의 `/api/v1/webhooks/*` 차단은 유지하며 Poller는 Docker 내부 `app:80` Webhook만 사용한다.

## 5. Gateway 배포

1. AI Gateway PostgreSQL과 현재 소스·Compose를 백업한다.
2. Migration `0008_community_assist_up.sql`을 적용한다.
3. `TECHFLOW_COMMUNITY_PUBLISH_ENABLED=true`로 Gateway를 기동한다.
4. Poller 최초 기동 로그가 `delivered=0`이고 기존 미답변 질문을 Seen 처리하는지 확인한다.
5. Health의 database/vector가 `ready`, 버전이 `0.9.0`인지 확인한다.

## 6. 승인 운영

담당자는 Case의 질문·초안·Citation·Draft Version을 확인한다.

- 승인: 편집 답변과 `expectedDraftVersion`을 Approve Flow에 전달한다.
- 반려: 사유와 같은 Version을 Reject Flow에 전달한다.
- 보류·근거 부족: 승인하지 않고 담당자 직접 답변이나 추가정보 요청으로 전환한다.

## 7. 롤백

- 신규 Flow 3개와 Poller만 DISABLED/중지한다.
- Gateway 이미지를 직전 Digest로 되돌리고 Compose를 백업본으로 복구한다.
- DB Down Migration은 생성된 Case·감사기록을 삭제하므로 제품 책임자의 명시적 승인과 백업 검증 후에만 실행한다.
- 이미 게시된 Community 답변은 자동 삭제하지 않는다. 게시물 ID를 근거로 담당자가 별도 판단한다.
- GitHub→Chat Flow, Event Gateway, Ingress와 SSRF Allowlist는 롤백 대상이 아니다.
