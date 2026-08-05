# TechFlow Parser·Embedding·검색 배포·운영 Runbook

> 대상: Issue #43, TechFlow AI Gateway 0.3.0
>
> 시험 서버 기준 경로: `/home/ablecloud/techflow-ai-gateway`

## 1. 목적과 경계

이 Runbook은 승인된 D0 Source Version을 실행하지 않고 Parser·Chunk·Embedding으로 변환하고, Source Scope를 선적용한 Hybrid Retrieval을 제공하며, 철회 시 파생 데이터를 삭제하는 절차를 정의합니다.

- Activepieces: Workflow 설계와 실행 순서를 담당합니다.
- AI Gateway: Source 상태, 승인, Parsing, Embedding, Retrieval, Lineage, 삭제를 담당합니다.
- OpenAI: Gateway가 선별한 D0 Chunk의 Embedding 또는 향후 답변 생성을 수행합니다.
- 원본 Repository는 OpenAI File·Vector Store에 업로드하지 않습니다.

## 2. 배포 전 확인

1. local `main`과 `upstream/main`이 일치해야 합니다.
2. 대상 Source Version은 `APPROVED`, `blockingViolationCount=0`이어야 합니다.
3. DB·현재 코드·Gateway Image ID를 백업합니다.
4. `.env`에는 Secret 값이 아니라 보호 파일 경로만 존재해야 합니다.
5. Root 여유 용량, Activepieces 6개 Container 상태를 기록합니다.

시험 서버의 Issue #43 배포 전 백업:

```text
/home/ablecloud/techflow-ai-gateway/backups/issue43-20260805T1444KST
```

백업에는 `techflow-rag.dump`, `pre-deploy-code.tgz`, `gateway-image-id.txt`, `checksums.sha256`가 포함됩니다.

## 3. 배포

```bash
cd /home/ablecloud/techflow-ai-gateway/deploy/compose/ai-gateway
docker compose --env-file .env config --quiet
./scripts/deploy.sh
docker compose --env-file .env run --rm migrate python scripts/migrate.py verify
```

성공 조건:

- Gateway `0.3.0`, Database·Vector `ready`
- Schema 19 Table, Issue #43 Column 8개
- Image 내부 Tree-sitter Parser File 13개
- Runtime `10001:10001`, Read-only Root FS, Capability Drop
- OpenAI API Key 환경변수 0건(Mock 배포 기준)

## 4. 승인 Source 인덱싱

```bash
python scripts/issue43_canary.py \
  --url http://127.0.0.1:8090 \
  --source-id <approved-source-id> \
  --profile GENIE_MASTER
```

API 순서는 다음과 같습니다.

1. `POST /v1/sources/{sourceId}/ingestions`
2. `POST /v1/jobs/{jobId}/run`
3. `POST /v1/rag/retrieve`

활성화 조건은 `indexedFileCount == eligibleFileCount`입니다. 불일치, Parser·Provider·DB 오류가 발생하면 Job은 `FAILED`, Source Version은 `APPROVED`로 복귀하고 부분 Chunk는 활성화하지 않습니다.

## 5. 검색 검증

검색은 다음 순서로 실행합니다.

1. D0, `ACTIVE`, Source Profile 또는 Compatibility Set 필터
2. FTS 20개 후보
3. Identifier 20개 후보
4. exact cosine 30개 후보
5. RRF `k=60`, `TEST_CODE` Weight 0.6
6. 상위 10개 반환

각 결과에서 Repository, Branch, Commit, Path, Start Line, End Line, Symbol을 확인합니다. 다른 Branch·미승인 Version의 결과가 한 건이라도 포함되면 실패입니다.

## 6. 실 OpenAI Embedding Canary

이번 서버 실증은 Mock Provider로 외부 호출 없이 완료했습니다. 실 Provider Canary는 운영자가 API Key를 보호 파일로 준비하고 다음 조건을 확인한 뒤 시행합니다.

1. `TECHFLOW_RAG_PROVIDER_MODE=openai`
2. `/run/secrets/openai_api_key` Read-only Mount
3. `TECHFLOW_OPENAI_API_KEY_FILE=/run/secrets/openai_api_key`
4. Key·요청 원문·응답 원문이 Log·DB·Issue에 없음
5. 반환 Model과 3072차원, Provider Request ID, Token, Latency만 감사 저장

OpenAI 요청은 공식 Embeddings API의 `model`, `dimensions=3072`, `encoding_format=float` 계약을 사용합니다.

## 7. 실패·재시도

- 같은 Job의 성공 결과는 `execution_idempotency_key`로 반복 반환합니다.
- 실패 Job은 새 Job과 새 멱등키로 재실행합니다.
- 사용자 질문·Source 원문·Secret은 오류 메시지에 포함하지 않습니다.
- 오류 코드만 `INDEXING_FAILED`, Failure Class와 함께 기록합니다.
- 새 Version이 전부 성공하기 전 기존 `ACTIVE` Version은 유지합니다.

## 8. 철회·삭제 Drill

Live Canary Source를 직접 철회하지 말고 DB 복제본에서 먼저 검증합니다.

1. 정확한 임시 DB 이름을 확인합니다.
2. Live DB를 임시 DB로 복제합니다.
3. `DELETE /v1/sources/{sourceId}`로 즉시 검색 제외합니다.
4. 생성된 `DELETION` Job을 `/run`합니다.
5. Chunk·Embedding·Symbol·Relation 삭제 수와 Ledger `SUCCEEDED`를 확인합니다.
6. 잔여 Chunk 0건을 확인합니다.
7. 임시 DB만 삭제합니다.

Issue #43 격리 Drill 결과는 64·64·15·45 삭제, 잔여 Chunk 0건입니다.

## 9. 롤백

애플리케이션 오류만 있는 경우 직전 Image ID로 Gateway를 복구합니다. Schema 롤백은 백업과 제품 책임자 승인 후 `0005_parser_embedding_retrieval_down.sql`을 적용합니다.

```bash
docker tag <previous-image-id> techflow/ai-gateway:<rollback-tag>
TECHFLOW_RAG_RELEASE=<rollback-tag> docker compose --env-file .env up -d gateway source-reconciler
curl -fsS http://127.0.0.1:18090/healthz
```

DB 복구가 필요한 경우 `techflow-rag.dump`를 새 DB에 복원해 검증한 뒤 전환합니다. Activepieces Volume과 Container는 AI Gateway 롤백 범위에 포함하지 않습니다.
