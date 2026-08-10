# TechFlow AI Gateway

TechFlow AI Gateway는 Activepieces와 AI Provider 사이에서 ABLESTACK 지식의 Source Registry, 검역·승인, Parser·Chunk·Embedding, 검색 범위와 인용, 삭제 정책을 소유하는 FastAPI 서비스입니다. 저장소 원문을 실행하지 않으며 Activepieces가 정책·상태·인프라 작업을 대신 소유하지 않습니다.

## v0.5.0 구현 범위

- Activepieces 5개 Flow용 최소 Event·Correlation·Idempotency 계약
- Ingestion Job·Evaluation Run `correlation_id` 영속화
- 9개 Source Profile Discovery·Scan 반복 실행 멱등성
- 승인·Compatibility·철회·평가 정책을 Gateway에 유지
- `RETRYABLE`·`TERMINAL`·`MANUAL_REVIEW` 실패 계약

- OpenAPI 21개 Operation, PostgreSQL RAG Table 19개
- 7개 영속 Bare Mirror, 9개 Allowlisted Source Profile
- `REGISTERED → QUARANTINED → APPROVED → INDEXING → ACTIVE` 상태 계약
- Markdown Heading Parser와 Tree-sitter Parser 13종
- Parser 실패 시 160 Line·Overlap 20의 결정론적 Fallback
- 최대 24 KiB Chunk, UUIDv5 기반 안정 ID, Source Version Lineage
- `text-embedding-3-large`, 3072차원, 공식 OpenAI Python SDK Adapter
- FTS 20·Identifier 20·exact cosine 30 후보와 RRF `k=60`
- 최종 최대 10개 Repository·Branch·Commit·Path·Line·Symbol 인용
- WITHDRAW 즉시 검색 제외와 Chunk·Embedding·Symbol·Relation 삭제 Ledger
- OpenAI Responses API의 `store=false`·`background=false`·Tool 0개·Strict Structured Output
- 단일 근거 `gpt-5.6-terra/medium`, 복합 근거 `gpt-5.6-sol/high` 결정론적 라우팅
- Branch·Compatibility·Test-only 사전 보류와 Citation 사후 검증
- `ANSWERED`·`ABSTAINED`·`FAILED`, 재시도·Circuit Breaker와 원문 없는 Provider 감사

`POST /v1/rag/query`는 `actorId`를 필수로 받아 안정적인 가명 `safety_identifier`를 만들고, 로컬에서 검색한 최대 10개 D0 Chunk만 답변 Provider에 전달합니다. 원본 질문·응답·Chunk는 Provider 감사 테이블에 저장하지 않습니다.

## 개발과 검증

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.lock
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/export_openapi.py
.venv/bin/python scripts/build_migration_manifest.py
.venv/bin/python ../../tools/ai_gateway/validate_issue_43.py
```

Memory·Mock 기본값은 네트워크 호출 없이 계약을 검증합니다.

```bash
TECHFLOW_RAG_STORE=memory TECHFLOW_RAG_PROVIDER_MODE=mock \
  .venv/bin/uvicorn app.main:app --port 8090
```

PostgreSQL Migration과 운영 Secret은 Runtime 환경 또는 보호된 파일로만 주입합니다.

```bash
TECHFLOW_RAG_MIGRATION_DSN='runtime-only' python scripts/migrate.py up
TECHFLOW_RAG_MIGRATION_DSN='runtime-only' python scripts/migrate.py verify
```

실 OpenAI 모드는 API Key 값을 환경변수나 문서에 기록하지 않고, 보호된 파일을 컨테이너 Secret으로 `/run/secrets/openai_api_key`에 마운트한 뒤 다음 참조만 설정합니다.

```text
TECHFLOW_RAG_PROVIDER_MODE=openai
TECHFLOW_OPENAI_API_KEY_FILE=/run/secrets/openai_api_key
TECHFLOW_OPENAI_PROJECT_ID_FILE=/run/secrets/openai_project_id
TECHFLOW_SAFETY_IDENTIFIER_SALT_FILE=/run/secrets/safety_identifier_salt
```

## 주요 자산

- OpenAPI: `openapi/techflow-ai-gateway-v1.json`
- Migration: `migrations/0000_*`부터 `migrations/0006_*`
- Migration Checksum: `migrations/manifest.json`
- Compose: `../../deploy/compose/ai-gateway/compose.yml`
- Source Runbook: `../../docs/runbooks/source-registry-quarantine.md`
- Parser·검색 Runbook: `../../docs/runbooks/parser-embedding-retrieval.md`
- 근거 답변 Runbook: `../../docs/runbooks/grounded-responses.md`
- Orchestration Runbook: `../../docs/runbooks/activepieces-rag-orchestration.md`
- 완료 보고서: `../../docs/reports/issue-45-activepieces-rag-orchestration-validation.md`
