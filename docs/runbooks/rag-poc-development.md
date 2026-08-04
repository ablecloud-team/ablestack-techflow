# TechFlow 문서·소스코드 RAG PoC 개발·검증 Runbook

> 대상: Issue #20, 하위 Issue #41~#46
>
> 개정: 2026-08-03 - OpenAI Responses·Embeddings 런타임과 모델 라우팅 포함

## 1. 목적

문서와 6개 소스 저장소를 9개 Source Profile로 안전하게 수집·색인하고, Cloud Branch와 미승인 저장소 조합이 섞이지 않는 근거 답변을 구현·검증하는 표준 절차다. 실제 운영 배포 전 PoC 개발 기준으로 사용한다.

## 2. 시작 조건

1. local `main`과 `upstream/main`이 일치한다.
2. [ADR-0008](../adr/0008-techflow-rag-poc-architecture.md), [ADR-0009](../adr/0009-openai-runtime-integration.md)과 [구조화 계약](../decisions/techflow-rag-poc-contract.json)이 승인됐다.
3. OpenAI API Project·Model 접근·Data Control 상태가 비밀정보 없이 확인됐고 Provider·DB·GitHub Credential은 런타임 주입 경로에만 존재한다.
4. `ablestack-docs`와 6개 소스 저장소의 지정 Branch가 Source Allowlist에 있다.
5. 대상 Commit과 Diff Summary를 Source 승인자가 확인했다.
6. Fetcher에 Hook·Build·Test·Shell 실행 권한이 없다.

## 3. 구현 순서

| 순서 | Issue | 종료 입력 |
|---:|---|---|
| 1 | #41 API·DB | Source·Compatibility·Provider Profile, Symbol·Relation·Provider Call Schema, Role Migration |
| 2 | #42 Fetch·Registry·검역 | 9개 Profile 최신 Head 후보·고정 Commit 승인·원자 활성화 |
| 3 | #43 Parse·Index·Retrieval·삭제 | AST/Fallback, OpenAI Embeddings, FTS·Identifier·Vector, Lineage |
| 4 | #44 답변·보류 | OpenAI Responses, Terra·Sol Routing, Structured Output, Citation 검증 |
| 5 | #45 Activepieces | Docs·Code 수집·재색인·평가 Flow |
| 6 | #46 품질·보안·E2E | 50개 Golden Set과 운영 증적 |

## 4. Source 기준선 확인

```text
SHARED_DOCS  ablecloud-team/ablestack-docs       master             50d50ad6c8c548dc58db866ca28b4cbb43cc74d0
CLOUD_MAIN   ablecloud-team/ablestack-cloud      main               a873fb1ff436990fd523e2fe56682ff7aa31d1ec
CLOUD_DIPLO  ablecloud-team/ablestack-cloud      ablestack-diplo    87beae809aa78af395c295eead50b0b8db220672
CLOUD_EUROPA ablecloud-team/ablestack-cloud      ablestack-europa   4787b6918bfa48a3d3665814f29ff23f9007fe1f
WALL_MAIN    ablecloud-team/ablestack-wall       main               f27b3f1b0b35489e05c64924b5cff7dc64dd2f6d
COCKPIT_DIPLO ablecloud-team/ablestack-cockpit-plugin ablestack-diplo 2018453077064a8a7fa92bcb4d8f531d8d1f8bb7
GENIE_MASTER ablecloud-team/ablestack-genie      master             3e3c5c364f5c7261b07d49fcbcd4f3605b91f3b1
KICKSTART_MASTER ablecloud-team/ablestack-kickstart master          ffe24390544dd58e3441ac7362fe46b93472d0e1
QEMU_EXEC_TOOLS_MAIN ablecloud-team/ablestack-qemu-exec-tools main  a4b9bd60bb93800612d96aaad84e73ddfd768b68
```

Branch Head가 바뀌면 새 Commit을 후보로만 등록한다. 운영자 승인과 전체 검역·색인 성공 전에는 기존 `ACTIVE` Version을 유지한다.

## 5. 파일 허용·검역

### 허용

- Docs: `docs/**/*.md`
- Backend·Script: `java`, `py`, `js`, `jsx`, `ts`, `tsx`, `vue`, `go`, `rb`, `groovy`, `cs`, `sh`, `bash`, `c`, `cc`, `cpp`, `h`, `hpp`, `rs`, `ps1`, `cmd`, `bat`
- UI: `html`, `htm`, `css`, `scss`, `sass`, `less`, `hbs`
- Build·Schema·Provisioning: `xml`, `sql`, `yaml`, `yml`, `properties`, `json`, `toml`, `ini`, `conf`, `cfg`, `service`, `spec`, `ks`, `repo`, `j2`, `tmpl`, `in`
- 저장소 문서: `md`, `mdx`, `adoc`, `rst`

### 차단

- `target`, `build`, `dist`, `node_modules`, `vendor`, `third_party`, `generated`, `gen`
- Minified, Binary, NUL, 비정상 Encoding, 1 MiB 초과
- Secret·개인정보·Credential URL 검출
- 승인되지 않은 Repository·Branch·Commit·Redirect

검역 실패 원문은 로그·Issue에 기록하지 않는다. Source ID, Path Hash, Rule ID, 상태만 남긴다.

## 6. 안전한 Source Fetch

1. Fetch 요청의 Repository·Branch·Commit이 Registry와 정확히 일치하는지 확인한다.
2. 임시 빈 Directory에서 Hook을 비활성화하고 고정 Commit Tree·Blob만 읽는다.
3. Checkout Script, Git LFS Smudge, Submodule, Build와 Test를 실행하지 않는다.
4. Blob SHA·Size·Path·Encoding을 검사한 후 허용 Text만 Parser에 전달한다.
5. Job 종료 후 임시 원문을 삭제하고 File Count·Hash·Duration만 기록한다.
6. 같은 Commit 재실행은 동일 Idempotency Key와 Content Hash로 중복을 만들지 않는다.

## 7. DB Bootstrap

- Database: `techflow_rag`
- Role: `techflow_rag_migrator`, `techflow_rag_app`, `techflow_rag_source_fetcher`
- Extension: `vector`, `pg_trgm`
- Activepieces DB Role과 공유 금지
- Compatibility Set·Symbol·Relation Table에 Source Profile·Branch·Commit Filter Index 생성
- Provider Profile과 `rag_provider_call`에는 Model·Request/Response ID·Token·Latency·상태만 저장하고 Prompt·응답 원문은 저장하지 않음
- Credential은 Compose Source, `.env.example`, Log, PR, Issue에 기록 금지

Migration 후 빈 DB에서 적용·Rollback·재적용을 검증한다.

## 8. Parser·Chunk 검증

### 문서

- Heading·Table·List·Code Block 보존
- 700 Token·Overlap 100

### Production Code

- Tree-sitter Symbol 단위, 1,200 Token·Overlap 120
- Package·Import·Annotation·Signature·Doc Comment·Line Range 보존
- Parser 실패 시 160 Line·Overlap 20 Fallback과 상태 기록

### Test·Schema

- Test는 `TEST_CODE`, Weight 0.6, 단독 답변 금지
- XML·SQL·YAML·Properties는 Logical Block으로 분할
- Chunk ID가 Repository·Branch·Commit·Path·Symbol·Line·Hash·Profile Version에 대해 결정적인지 확인

## 9. 검색 검증

1. Query에 `sourceProfileIds` 또는 승인된 `compatibilitySetId`를 지정한다.
2. SQL 후보 생성 전에 D0·ACTIVE·Source Profile·Compatibility Set·Branch·Commit Filter를 적용한다.
3. FTS 20, Identifier 20, exact cosine 30 후보를 생성한다.
4. RRF `k=60`과 Test Weight를 적용한다.
5. 최종 10개, Source Version당 4개 제한을 확인한다.
6. 다른 Cloud Branch 또는 미승인 저장소 조합의 Chunk가 1개라도 섞이면 실패 처리한다.

활성 Chunk가 50,000개 이상이면 exact와 HNSW를 같은 Golden Set으로 비교한다. Recall 손실 2%p 이하와 P95 개선을 충족할 때만 Profile별 HNSW 변경 제안을 만든다.

## 10. 답변 검증

- 답변이 Source Profile·Compatibility Set·Branch·Commit을 명시한다.
- 코드 Citation의 Path·Start Line·End Line·Symbol이 고정 Commit에서 해석된다.
- 문서·코드가 충돌하면 충돌을 표시하거나 보류한다.
- Test-only, Branch 미지정, Cross-Branch, 미승인 Cross-Repository, 근거 부족은 `ABSTAINED`다.
- AI Tool·Shell·API·Flow·ABLESTACK·Source Code 실행 경로가 없다.
- Prompt·응답 원문이 DB·Redis·Log·Metric에 남지 않는다.
- Responses 요청에 `store=false`, `background=false`, Tool 0개와 Structured Output이 적용된다.
- Gateway가 반환 Citation을 현재 Context와 Source Version에 대해 다시 검증한다.
- 기본 `gpt-5.6-terra/medium`과 사전 규칙 기반 `gpt-5.6-sol/high` 승격만 허용한다.
- 낮은 자신감이나 Provider 오류 때문에 자동 두 번째 Model 호출이 발생하지 않는다.
- 개인 사용자는 단방향 가명화한 안정적인 `safety_identifier`를 사용한다.

## 10.1 OpenAI Adapter 검증

1. 공식 Python SDK의 Responses API와 Embeddings API Adapter만 활성화한다.
2. 원본 Repository·OpenAI File·Vector Store·ChatGPT Project 업로드 경로가 없음을 확인한다.
3. Query Context는 최종 최대 10개 D0 Chunk와 Citation Metadata만 포함한다.
4. 최초 대량 색인·전체 재색인·평가만 Batch API 후보이며 증분 색인은 동기 Embeddings API를 사용한다.
5. Connect 3초·전체 12초, 429·5xx·Network Timeout 최대 3회와 Circuit Breaker를 검증한다.
6. `rag_provider_call`에 Raw Prompt·Raw Response·Credential이 없음을 확인한다.
7. OpenAI Organization·Project의 ZDR·MAM·Data Residency 상태를 배포 증적에 기록한다. `store=false`만으로 ZDR이라고 판정하지 않는다.

## 11. Golden Set

- 총 50개 이상
- Code 질문 20개 이상
- Cloud main·Diplo·Europa 차이 5개 이상
- Component Repository 질문을 저장소별 최소 1개 포함
- 문서·코드 교차 검증 5개 이상
- 근거 없음·Test-only·충돌 보류 5개 이상

각 Case는 Source Profile, Compatibility Set, Commit, Expected Source Kind, Repository·Path·Symbol·Line Range, 필수 개념, 금지 주장과 기대 상태를 가진다.

## 12. 삭제 Drill

1. 대상 Profile의 활성 Source Version을 `WITHDRAWN`으로 전환한다.
2. 즉시 Retrieval 후보가 0건인지 확인한다.
3. Chunk·Embedding·Symbol·Relation·Cache·Evaluation Link를 Lineage로 조회한다.
4. 테스트 환경 15분 내 잔여 0건을 확인한다.
5. Deletion Ledger에는 시각·대상 건수·결과만 남긴다.
6. 격리 복구 후 Ledger를 재적용하고 다시 0건을 확인한다.

## 13. Activepieces Flow

| Flow | 입력 | 출력 |
|---|---|---|
| Discovery | Source ID·Branch | 후보 Commit·Diff Summary |
| Approval | 후보 Version·검역 요약 | 승인·거부 ID |
| Ingestion | 승인 Version·Idempotency Key | Job ID |
| Evaluation | Source Profile·Compatibility Set·Commit·Provider Profile | Evaluation Run ID |

Flow에는 코드 원문·Provider Key·GitHub Token을 저장하지 않는다. AI Gateway의 `SUCCEEDED`와 품질 Gate 통과를 분리한다.

## 14. 배포

1. Runtime·DB·Secret Store 백업
2. Migration과 Extension 검증
3. Gateway·Fetcher Image Digest와 Parser Dependency 잠금
4. 내부 Network에만 배포
5. `/healthz`, Mock Provider, Parser Health 확인
6. OpenAI API Project의 Model 접근·ZDR/MAM·Data Residency 상태 확인
7. 문서와 8개 코드 Source Profile의 소형 Canary 순차 검증
8. 전체 승인 Commit 색인
9. 50개 Golden Set·Branch Isolation·Compatibility Set·Model Routing·삭제 Drill 통과
10. Activepieces Flow Publish

## 15. 롤백

1. RAG Flow 비활성화
2. 실패한 Source Profile만 검색 제외
3. 직전 승인 Commit 또는 빈 Index로 전환
4. Gateway·Fetcher 직전 Digest 복귀
5. 삭제 Ledger 재적용
6. Chunk·Embedding·Symbol·Relation 잔여와 기존 Active Profile 정상성을 확인

## 16. 완료 증적

- 승인 Source·Branch·Commit·File Count
- 검역 Rule별 통과·차단 건수
- Parser 성공·Fallback·실패 건수
- Profile별 Chunk·Symbol·Relation·Embedding 건수
- Branch Isolation과 Code Line Citation 결과
- Golden Set·P95·Provider 오류·보류 결과
- Model Profile별 Token·Latency·비용·Structured Output·Citation 사후 검증 결과
- OpenAI API Project Data Control 상태와 Tool·File·Vector Store 호출 0건 증적
- 삭제·복구 Drill
- Markdown 보고서, PDF 보고서, PPTX/PDF 발표자료, Artifact Manifest
