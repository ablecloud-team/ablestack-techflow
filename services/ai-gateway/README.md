# TechFlow AI Gateway

Issue #41에서 구현한 Python 3.12/FastAPI 기반 RAG 실행 골격이다. 이 단계는 Source·Compatibility·Job·Query·Evaluation API, PostgreSQL Schema, Provider Profile과 Mock Adapter의 책임 경계를 구현한다.

## 구현 범위

- 11개 OpenAPI Operation
- 15개 PostgreSQL 논리 Table
- `techflow_rag_migrator`, `techflow_rag_app`, `techflow_rag_source_fetcher` Group Role
- `vector`, `pg_trgm`
- `OPENAI_RAG_DEFAULT_V1`, `OPENAI_RAG_ESCALATION_V1`, `OPENAI_EMBEDDING_V1`
- Mock Responses·Embeddings Adapter
- 변경 요청 `Idempotency-Key`, 전체 v1 요청 `X-Correlation-Id`
- Raw Prompt·응답·Authorization·Credential을 저장하지 않는 `rag_provider_call`
- 비루트 UID 10001, Read-only Root FS, Capability Drop, Digest 고정 Base Image

## 의도적으로 제외한 범위

- 실제 GitHub Source Fetch: #42
- 실제 문서·코드 Parsing·OpenAI Embeddings·Hybrid Retrieval: #43
- 실제 OpenAI Responses·모델 라우팅·Citation 답변: #44
- Activepieces Flow: #45
- Golden Set·운영 E2E: #46

`POST /v1/rag/query`는 #43 이전에 Provider를 호출하지 않고 `ABSTAINED`를 반환한다. `TECHFLOW_RAG_PROVIDER_MODE`는 `mock`만 허용하며 실제 OpenAI API Key는 필요하지 않다.

## 개발 실행

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
$env:TECHFLOW_RAG_STORE = "memory"
$env:TECHFLOW_RAG_PROVIDER_MODE = "mock"
.venv\Scripts\python.exe -m uvicorn app.main:app --port 8090
```

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.lock
TECHFLOW_RAG_STORE=memory TECHFLOW_RAG_PROVIDER_MODE=mock \
  .venv/bin/uvicorn app.main:app --port 8090
```

## 검증

```bash
python -m unittest discover -s tests -v
python scripts/export_openapi.py
python scripts/build_migration_manifest.py
python ../../tools/ai_gateway/validate_issue_41.py
```

PostgreSQL이 준비된 환경에서는 Migration DSN을 보호된 런타임 환경으로만 주입한다.

```bash
TECHFLOW_RAG_MIGRATION_DSN='runtime-only' python scripts/migrate.py up
TECHFLOW_RAG_MIGRATION_DSN='runtime-only' python scripts/migrate.py verify
```

Rollback은 데이터를 삭제하므로 Flow 중지·백업·승인 후에만 실행한다.

```bash
TECHFLOW_RAG_MIGRATION_DSN='runtime-only' \
  python scripts/migrate.py down --allow-destructive-rollback
```

## API 필수 Header

- 모든 `/v1/*`: `X-Correlation-Id`
- POST·DELETE 변경 요청: `Idempotency-Key`
- Query: 요청 Body의 `queryId`

Validation 오류는 입력값을 되돌려 주지 않는다. Application Log는 Correlation ID, Method, Route, Status, Duration과 오류 Type만 포함한다.

## 주요 자산

- OpenAPI: `openapi/techflow-ai-gateway-v1.json`
- Migration: `migrations/0000_*`, `migrations/0001_*`
- Migration Checksum: `migrations/manifest.json`
- Docker Compose: `../../deploy/compose/ai-gateway/compose.yml`
- 운영 Runbook: `../../docs/runbooks/ai-gateway-foundation.md`
