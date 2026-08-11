# ABLESTACK Assist 종합·멀티모달·로그 배포·운영 Runbook

## 배포 대상과 금지 대상

배포 대상은 `/home/ablecloud/techflow-ai-gateway`의 AI Gateway와 새 Assist Flow뿐이다. 동결 서비스 `github-chat-v1`의 훅 경로, Flow ID, Activepieces GitHub→Chat Flow, Event Gateway Adapter, Caddy 라우팅, SSRF 허용 목록은 변경하지 않는다.

## 배포 전

1. `protected_service_guard.py`가 `github-chat-v1 state=frozen guard=passed`를 반환하는지 확인한다.
2. AI Gateway DB Dump, 소스, 이전 Image ID를 같은 타임스탬프 백업 디렉터리에 저장한다.
3. Secret File과 `.env` 본문은 백업 아카이브·Git·보고서에 넣지 않는다.
4. 로컬에서 `python -m unittest discover -s services/ai-gateway/tests`와 `git diff --check`를 통과시킨다.

## AI Gateway 배포

```bash
cd /home/ablecloud/techflow-ai-gateway/deploy/compose/ai-gateway
sed -i 's/^TECHFLOW_RAG_RELEASE=.*/TECHFLOW_RAG_RELEASE=issue-57-log-artifacts/' .env
docker compose --env-file .env -f compose.yml -f compose.openai.override.yml config -q
docker compose --env-file .env -f compose.yml -f compose.openai.override.yml build gateway migrate artifact-init
docker compose --env-file .env -f compose.yml -f compose.openai.override.yml up -d --no-build gateway source-reconciler
curl -fsS http://127.0.0.1:18090/healthz
```

Artifact 전용 Volume은 `artifact-init`이 UID 10001 소유·0700으로 초기화한다. Gateway만 재배포할 때는 `up -d --no-deps --no-build gateway`를 사용한다.

## Activepieces 배포

`manage-rag-flows.py`에 Assist 번들만 지정한다. 로그인 값은 현재 프로세스 환경에만 주입하고 명령 종료 즉시 해제한다.

```bash
python3 scripts/manage-rag-flows.py \
  --base-url http://172.16.0.231:8080 \
  --bundle flows/assist-orchestration-v1.json
```

외부 Caddy는 일반 `/api/v1/webhooks/*`를 계속 차단한다. 시험은 내부 App Network에서 수행하며 Flow Run의 `status=SUCCEEDED`, HTTP Action의 Gateway 응답 `status=200`, 동일 Correlation ID를 확인한다.

## 검증

1. 범위 없는 Cloud 질문이 Provider 호출 없이 `NEEDS_INFORMATION`인지 확인한다.
2. 승인 Compatibility Set으로 복수 저장소 질문을 수행하고 모든 Citation이 세트 구성원인지 확인한다.
3. 1200×720 합성 PNG를 업로드하고 화면 텍스트·합성 표시를 모두 관찰하는지 확인한다.
4. 1×1 PNG는 판독 불가능하다고 보류하는지 확인한다.
5. Artifact 삭제 후 `GET`이 404인지 확인한다.
6. UTF-8 `.log`를 업로드하고 비밀정보가 `[REDACTED]`된 오류 주변 행만 답변 근거로 사용되는지 확인한다.
7. ZIP과 TAR.GZ 로그가 Member 경로·행 번호를 유지하는지 확인한다.
8. 경로 탈출, 압축률 20:1 초과, 100개 초과 Member, 중첩 Archive, Binary·D1 로그를 400으로 거부하는지 확인한다.
9. 동결 서비스 보호 가드를 다시 실행한다.

## 장애 처리와 롤백

| 증상 | 처리 |
|---|---|
| `PROVIDER_TIMEOUT` | 연결 장애와 읽기 지연을 구분한다. 현재 연결 3초, 읽기 90초, 재시도 1회다. |
| `PROVIDER_INVALID_RESPONSE` | raw 응답을 기록하지 않고 Schema·Citation·Artifact ID 검증 실패로 처리한다. |
| Artifact 400 | 형식·매직 바이트·크기·해상도·UTF-8·D0와 Archive 경로·파일 수·압축률·중첩 여부를 확인한다. |
| 로그 증거 없음 | Error/Warn이 없으면 처음·마지막 20행을 사용한다. 여전히 비어 있거나 Binary면 업로드를 거부한다. |
| 로그 일부 잘림 | `evidenceTruncated=true`와 Member별 행 범위를 확인하고 질문을 좁히거나 로그를 분리한다. |
| Gateway 비정상 | 이전 Image ID로 `.env` Release를 복원하고 Gateway만 재생성한다. |
| DB 문제 | 배포 전 Dump를 새 DB에서 복원해 확인한 뒤 전환한다. |
| Assist Flow 문제 | 신규 Flow만 DISABLED하고 기존 RAG 및 GitHub→Chat Flow는 변경하지 않는다. |

시험 서버 최초 배포 백업은 `/home/ablecloud/techflow-ai-gateway-backups/issues56-58-20260811T060003Z`, 로그 보완 직전 DB Dump·소스·Image ID 백업은 `/home/ablecloud/techflow-ai-gateway-backups/log-artifacts-20260811T073757Z`에 보관했다. 로그 보완 최종 Image ID는 `sha256:9f5fd5da418b26072af506df2d876304ca8be1a5efd7a0b1a4fe9d42b21729ee`다.
