# TechFlow AI Gateway

Issue #41의 Python 3.12/FastAPI 기반에 Issue #42 Source Registry·영속 Bare Mirror·검역·사람 승인 Gate를 확장한 서비스다. Activepieces는 업무 오케스트레이션을 담당하고, 이 서비스가 Source 상태·정책·미러·멱등성·원자 활성화를 소유한다.

## 구현 범위

- 19개 OpenAPI Operation
- 19개 PostgreSQL 논리 Table
- 7개 저장소·9개 불변 Source Profile, 초기 Reviewer `dhslove`
- 7개 영속 Bare Mirror와 Profile별 보호 Candidate Ref
- 실제 6시간 Reconciler, 24시간 Stale 판정, `GET /v1/source-mirrors`
- 발견 시에만 GitHub Fetch, 스캔은 Local-only `ls-tree`·`cat-file`
- D0 경로·Binary·Encoding·크기·Secret·PII·Prompt Injection 검역
- `REGISTERED` → `QUARANTINED` → `APPROVED` → `INDEXING` → `ACTIVE` 상태 계약
- Mock Responses·Embeddings Adapter; 실제 OpenAI 호출 없음
- UID 10001, Read-only Root FS, Capability Drop, Digest 고정 Base Image

Parser·Chunk·Embeddings·Hybrid Retrieval은 #43, Responses·모델 라우팅은 #44, Activepieces Push·승인 Flow는 #45, Golden Set·E2E는 #46 범위다. `POST /v1/rag/query`는 #43 이전에 Provider를 호출하지 않고 `ABSTAINED`를 반환한다.

## 저장·갱신 구조

`source-reconciler`는 시작 시와 21,600초마다 9개 Profile의 발견 API를 호출한다. Fetch 결과는 Docker Named Volume `techflow_source_mirrors`의 저장소별 Bare Mirror에 유지하고, Commit을 Candidate Ref로 보호한다. 스캔은 네트워크를 사용하지 않는다. D0 적격 Blob은 PostgreSQL에 저장한다.

GitHub 장애 시 신규 Head 발견은 지연되지만 기존 Mirror의 고정 Commit 스캔과 향후 승인 Index 질의는 계속 가능하다. Push Webhook 즉시 갱신은 현재 미구현이며 #45에서 연결한다.

## 개발·검증

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.lock
TECHFLOW_RAG_STORE=memory TECHFLOW_RAG_PROVIDER_MODE=mock \
  .venv/bin/uvicorn app.main:app --port 8090
```

```bash
python -m unittest discover -s tests -v
python scripts/export_openapi.py
python scripts/build_migration_manifest.py
python ../../tools/ai_gateway/validate_issue_41.py
python ../../tools/ai_gateway/validate_issue_42.py
```

PostgreSQL Migration DSN과 모든 Secret은 Runtime 환경 또는 보호 파일로만 주입한다.

```bash
TECHFLOW_RAG_MIGRATION_DSN='runtime-only' python scripts/migrate.py up
TECHFLOW_RAG_MIGRATION_DSN='runtime-only' python scripts/migrate.py verify
```

## 주요 자산

- OpenAPI: `openapi/techflow-ai-gateway-v1.json`
- Migration: `migrations/0000_*`부터 `migrations/0004_*`
- Migration Checksum: `migrations/manifest.json`
- Docker Compose: `../../deploy/compose/ai-gateway/compose.yml`
- 기반 Runbook: `../../docs/runbooks/ai-gateway-foundation.md`
- Source 운영 Runbook: `../../docs/runbooks/source-registry-quarantine.md`
