# Issue #44 OpenAI Responses·근거 답변 구현 완료 보고서

## 1. 결론

Issue #44 범위를 구현하고 시험 서버에 TechFlow AI Gateway 0.4.0을 배포했다. 실 OpenAI Responses 호출은 `ANSWERED`와 Commit 고정 Citation 5개를 반환했고, 검색 근거가 없는 질의는 `ABSTAINED`와 `generationProviderCalled=false`로 종료됐다. 로컬·서버 격리 테스트 각 96개, Secret Scan 0건, `0.4.0 → 0.3.0 → 0.4.0` 롤백·복귀를 통과했다.

## 2. 구현 결과

| 항목 | 구현 |
|---|---|
| Responses Adapter | 공식 OpenAI Python SDK, Runtime Secret File, Project 격리 |
| 최소 전송 | 로컬 검색 최종 D0 Chunk 최대 10개 |
| 요청 통제 | `store=false`, `background=false`, `stream=false`, Tool 0개 |
| 출력 계약 | strict JSON Schema: State·Answer·Citation IDs·Abstain Reason |
| 기본 라우팅 | 단일 Repository·Commit은 `gpt-5.6-terra/medium` |
| 상향 라우팅 | 승인 Compatibility 범위의 복수 Repository·Commit은 `gpt-5.6-sol/high` |
| 사전 보류 | 근거 없음, Test-only, Branch 충돌, 미승인 Cross-repository |
| 사후 검증 | Citation 부분집합, 답변당 Citation 필수, Test-only·Branch 재검증 |
| 상태 | `ANSWERED`, `ABSTAINED`, `FAILED` |
| 장애 | 3초 Connect·12초 응답, 최대 3회, Circuit Breaker |
| 감사 | 원문 없는 Profile·Model·ID·Token·Latency·Status·Error |

## 3. 동작 구조

```mermaid
flowchart LR
    Q["질의·actorId·Scope"] --> R["Hybrid Retrieval"]
    R --> P{"사전 정책"}
    P -->|근거 없음·충돌| A["ABSTAINED"]
    P -->|단일 Version| T["Terra medium"]
    P -->|복수 승인 구성| S["Sol high"]
    T --> V["Strict Schema·Citation 재검증"]
    S --> V
    V --> OK["ANSWERED"]
    V --> AB["ABSTAINED"]
    T -. 장애 .-> F["FAILED"]
    S -. 장애 .-> F
```

모델은 라우팅을 스스로 선택하지 않는다. Gateway가 검색 Metadata만으로 한 번 판정하고, 기본 호출 실패나 낮은 확신을 이유로 자동 이중 호출하지 않는다.

## 4. 실증 증거

| 검증 | 결과 |
|---|---|
| 로컬 Unit·Contract | 96 passed |
| 서버 Network-none Container | 96 passed |
| 저장소 계약 Validator | 21 Operations, Context 10, Responses Profile 2 |
| 실 Responses 답변 | `ANSWERED`, 기본 Profile, Citation 5, Provider 호출 성공 |
| 실 사전 보류 | `ABSTAINED`, Citation 0, Generation Provider 미호출 |
| Provider 성공 감사 | Input 6,002 Token, Output 620 Token, 6,184 ms, Request·Response ID 존재 |
| 활성 색인 | 34 File, 64 Chunk, 64 Embedding, 15 Symbol, 45 Relation |
| Secret Scan | 배포 파일 0, Gateway Log 0 |
| Root Disk | 1,005 GiB, 가용 950 GiB, 사용률 2% |
| Activepieces | 6개 Container 모두 Healthy 유지 |

초기 Canary에서 두 가지 운영 결함을 발견하고 수정했다.

1. HMAC 가명 식별자가 67자로 OpenAI의 64자 제한을 초과했다. Digest를 잘라 최대 64자로 고정했다.
2. 동일 Source Version의 문서·코드 혼합을 복합 분석으로 과대 판정해 Sol/high를 선택했고 12초 정책 내 응답하지 못했다. 혼합 Source Kind 자체는 충돌이 아니므로 단일 Repository·Commit은 Terra로 유지했다.

두 실패는 각각 `PROVIDER_REJECTED/TERMINAL`, `PROVIDER_TIMEOUT/RETRYABLE`로 원문 없이 감사됐다. 수정 후 실 답변이 성공했다.

## 5. Secret과 데이터 보호

사용자가 제공한 OpenAI Key·Project 식별자는 GitHub Repository Secrets와 서버 런타임 Secret File로만 배치했다. 저장소에는 Secret 이름과 파일 경로만 존재하며 실제 값은 없다. `actorId`는 서버 전용 Salt와 HMAC-SHA256으로 가명화하고 OpenAI 제한에 맞춰 64자로 제한한다.

`rag_provider_call`은 질문·Context·답변을 저장하지 않는다. Canary도 답변 원문 대신 상태, Profile, Citation 수, Answer 문자 수와 호출 여부만 출력한다.

## 6. 배포·복구

배포 전 PostgreSQL Dump, 기존 Image ID, Compose·Override·환경 참조, Runtime Source와 Checksum을 `/home/ablecloud/techflow-ai-gateway/backups/issue44-predeploy-20260810T0230KST`에 보관했다. 별도 Stage에서 이미지를 빌드하고 96개 격리 테스트를 통과한 뒤 운영 Compose를 재생성했다.

롤백 시험은 기존 v0.3.0으로 전환해 Provider `openai`와 Health를 확인하고, 다시 v0.4.0 Image로 복귀해 Database·Vector `ready`를 확인했다. 데이터 Schema 변경이 없어 활성 색인은 유지됐다.

## 7. 조사 결과와 운영 확인 항목

OpenAI 공식 지침상 현재 모델 선택은 기본 `gpt-5.6-terra`, 고난도 작업은 `gpt-5.6-sol` 경로와 일치한다. Structured Output은 Responses API의 strict `text.format` JSON Schema를 사용했다. `store=false`는 애플리케이션 수준 데이터 최소화 통제로 유지한다.

제품 책임자의 2026-08-10 결정에 따라 Zero Data Retention은 사용하지 않으며 기존의 Dashboard 미확인 운영 Gate는 폐기한다. D0 PoC의 구현 경계는 유지하고 D1 이상 데이터 확대는 비식별화·최소화, 접근권한, 감사, 보존·삭제 및 사고 대응을 포함한 TechFlow 제품 보안심사로 결정한다.

- [OpenAI 최신 모델 선택 지침](https://developers.openai.com/api/docs/guides/latest-model)
- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [OpenAI API 데이터 제어](https://developers.openai.com/api/docs/guides/your-data)

## 8. 완료 판정과 다음 단계

Issue #44의 구현·실 Provider·보류·오류·감사·Secret·배포·롤백 조건을 모두 충족했다. PR 검토·병합 전까지 Issue는 열어 두며, 다음 구현 단위는 Issue #45의 Activepieces Push·승인·재색인 연동이다.

OpenAI Dashboard의 데이터 보존 제어 상태는 더 이상 운영자 확인 항목이 아니다. 대화에 직접 입력된 현 API Key 교체는 제품 책임자의 기존 결정에 따라 명시적으로 요청될 때까지 보류한다.

고객 공개 여부는 제품 책임자의 결정이며 본 구현 범위나 향후 자체 기능 구현을 제한하지 않는다.
