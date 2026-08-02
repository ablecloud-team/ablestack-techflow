# TechFlow RAG PoC 개발·검증 Runbook

> 대상: Issue #20, 하위 Issue #41~#46
>
> 설계 계약: [techflow-rag-poc-contract.json](../decisions/techflow-rag-poc-contract.json)

## 1. 목적

Issue #20의 하위 구현이 동일한 Source, 데이터 등급, API, 검색, 답변, 실패, 삭제와 평가 계약을 유지하도록 개발 시작·검토·통합·배포 순서를 정의한다. 이 Runbook은 실제 운영 절차가 아니라 P1 PoC 구현과 검증 절차다.

## 2. 작업 시작 전 공통 확인

1. 로컬 `main`과 `upstream/main`을 동기화한다.
2. 해당 하위 Issue 전용 Branch를 최신 로컬 `main`에서 만든다.
3. 선행 Issue가 병합·종료됐는지 확인한다.
4. 구조화 계약 Validator와 기존 회귀 테스트를 실행한다.
5. Secret·Provider·Database Credential은 런타임으로만 전달한다.
6. Source Commit과 허용 경로가 설계 계약과 일치하는지 확인한다.

```bash
python3 tools/rag/validate_rag_poc_contract.py \
  docs/decisions/techflow-rag-poc-contract.json

python3 -m unittest -v tools.rag.test_validate_rag_poc_contract
```

## 3. 구현 순서

| 순서 | Issue | 시작 조건 | 종료 Gate |
|---:|---|---|---|
| 1 | #41 Gateway·API·DB | Issue #20 설계 승인 | OpenAPI·Migration·격리 Role |
| 2 | #42 Registry·Quarantine | #41 병합 | D0 Allowlist·승인·거부 |
| 3 | #43 Chunk·Embedding·Retrieval·삭제 | #42 병합 | Hybrid 검색·Lineage·삭제 |
| 4 | #44 답변·Provider·보류 | #43 병합 | Citation·보류·Tool 차단 |
| 5 | #45 Activepieces Flow | #42~#44 병합 | 멱등성·Correlation·실패 분류 |
| 6 | #46 품질·보안·E2E | #44·#45 병합 | Golden Set·운영 증적 |

## 4. Issue #41 시작 입력

다음 값은 저장소에 기록하지 않고 보호 저장소 또는 대화형 입력으로만 제공한다.

- Provider Endpoint
- Chat Model 이름
- Embedding Model 이름과 Dimension
- Provider Credential
- RAG Database App·Migration Credential
- GitHub API 인증 사용 여부와 Credential
- 평가 Reviewer

값이 준비되지 않아도 Provider·GitHub Mock 기반 구현은 진행할 수 있다. 실제 Provider E2E는 Runtime 입력이 준비된 뒤 수행한다.

## 5. Source 검증

P1 허용 Source는 다음과 같다.

```text
repository = ablecloud-team/ablestack-docs
branch = master
path = docs/**/*.md
classification = D0
```

수집 시 Branch 최신 상태를 바로 색인하지 않는다. 현재 Commit을 후보 Version으로 등록하고 검역·운영자 승인 후에만 활성화한다.

검증 항목:

- Repository·Branch·Path Allowlist
- Commit SHA, Blob SHA, Content Hash
- Markdown MIME·Encoding·Size
- Secret·개인정보·악성 지시·Unsafe Link
- 승인자·승인 시각·승인 Version

검사 실패 원문은 로그·Issue에 남기지 않는다. Source ID, 검출 규칙 ID, 파일 경로 Hash와 상태만 기록한다.

## 6. Database Bootstrap

1. PostgreSQL·Redis 상태 백업을 수행한다.
2. 보호된 PostgreSQL 관리자 Credential로 `techflow_rag` Database를 생성한다.
3. `techflow_rag_migrator`와 `techflow_rag_app` Role을 분리한다.
4. `vector` Extension을 RAG Database에 활성화한다.
5. Migration Role로 Schema를 적용한다.
6. App Role이 DDL·다른 Database·Activepieces Table에 접근하지 못하는지 검사한다.
7. Migration 재실행과 역방향 호환성을 검증한다.

Database Credential은 `.env.example`, Compose Source, Log, PR, Issue와 보고서에 기록하지 않는다.

## 7. Provider Profile 등록

Provider Profile에는 Endpoint, Chat Model, Embedding Model, Dimension과 Version만 기록한다. Credential 값은 보호 저장소 참조를 통해 런타임 주입한다.

확인 항목:

- 입력 보존·학습 비활성화
- D0만 전송
- Timeout·429·5xx 처리
- Token·비용 상한
- 요청·응답 원문 로그 비활성화
- Tool·Function Calling 비활성화

Embedding Profile 변경은 새 Vector 세대를 만들고 Golden Set 비교 후 전환한다. 기존 Vector를 제자리에서 덮어쓰지 않는다.

## 8. Activepieces Flow 검토

Flow가 전달할 수 있는 필드:

```text
correlationId, sourceId, sourceVersion, jobId
operation, status, errorCode, failureClass
evaluationRunId
```

전달 금지 필드:

```text
documentBody, prompt, answer, providerCredential
databaseCredential, authorizationHeader, secret
```

Flow의 성공은 HTTP 2xx만으로 판단하지 않는다. AI Gateway의 상태와 결과 계약을 확인한다. 불명확한 결과는 `UNKNOWN` 또는 `MANUAL_REVIEW`로 처리하고 자동 재전송하지 않는다.

## 9. Golden Set 실행

1. Golden Case Version과 Provider·Embedding·Chunk Profile Version을 고정한다.
2. Index Commit과 활성 Source 수·Chunk 수를 기록한다.
3. 30개 이상의 Case를 실행한다.
4. Citation, Expected Source Recall, 금지 주장, 결과 상태, 지연·Token을 수집한다.
5. Reviewer가 정확성·유용성을 평가한다.
6. 기준 미달 Case를 Category별로 분석한다.
7. 변경 후 전체 Golden Set을 다시 실행한다.

완료 기준:

- Citation 100%
- 수용 가능 답변 80% 이상
- 올바른 보류 90% 이상
- 정상 Provider P95 10초 이하
- Restricted Data·Secret·파생 데이터 잔존 0건

## 10. Source 철회·삭제 검증

1. 활성 Source Version을 철회한다.
2. 같은 Transaction 또는 상태 전환 직후 검색 후보에서 제외됐는지 확인한다.
3. Source ID로 Chunk·Embedding·Cache·평가 연결을 조회한다.
4. 삭제 Job을 실행한다.
5. 테스트 환경에서는 15분 이내 파생 행 0건을 확인한다.
6. 삭제 건수·시각·상태를 Ledger에 기록한다.
7. 백업 복구 Drill 후 Ledger를 재적용해 재등장하지 않는지 확인한다.

운영 상한은 7일이며 SLO 위반은 `MANUAL_REVIEW`와 경보 대상이다.

## 11. 실패와 재처리

| 실패 분류 | 재시도 | 예 |
|---|---|---|
| `RETRYABLE` | 최대 3회, 지수 Backoff | 429, 5xx, Timeout |
| `TERMINAL` | 없음 | 등급·Allowlist·Schema·Secret 위반 |
| `MANUAL_REVIEW` | 담당자 승인 후 | 출처 충돌, 악성 지시 의심, 삭제 불완전 |

재시도는 같은 Idempotency Key를 사용한다. 새로운 Key로 같은 작업을 반복해 중복 Source·Chunk·Provider 비용을 만들지 않는다.

## 12. 배포 전 검증

- 모든 단위·계약·통합·보안 테스트 통과
- 구조화 계약 Validator 통과
- Image·의존성 Version·Digest 잠금
- Secret Scan 0건
- 외부 AI Gateway Route 없음
- Egress 목적지 Allowlist 확인
- DB Role 격리 확인
- Backup·Rollback Point 기록
- Test Source Canary와 Golden Set 통과
- Source 철회·삭제 검증 통과

## 13. 롤백

1. RAG Activepieces Flow를 비활성화한다.
2. AI Gateway 호출 경로를 비활성화한다.
3. 신규 Source Version을 검색에서 제외한다.
4. 직전 활성 Version 또는 빈 Index로 전환한다.
5. Runtime Image Lock을 직전 Version으로 복원한다.
6. RAG Database는 조사와 증적을 위해 보존한다.
7. 삭제 요청이 있으면 복구 전후에 Ledger를 재적용한다.

Activepieces, PostgreSQL·Redis Volume 또는 기존 GitHub Chat Flow를 삭제하지 않는다.

## 14. Issue 완료 증적

각 하위 Issue는 다음을 남긴다.

- 구현 PR과 Merge Commit
- 자동 테스트·보안 테스트 결과
- 배포 또는 Mock E2E 결과
- 변경된 API·Schema·Flow Version
- Rollback 기준과 실제 확인
- Secret Scan 결과
- Runbook·완료 보고서 갱신

Issue #46은 전체 Markdown 보고서, PDF 보고서, PPTX/PDF 발표자료와 Artifact Manifest를 생성한다.
