# ADR-0007: TechFlow 데이터 분류·보존·삭제 정책

- 상태: 승인
- 결정일: 2026-08-01
- 적용 이슈: [#39 TechFlow 보안 위협 모델 및 데이터 분류·보존 정책 확정](https://github.com/ablecloud-team/ablestack-techflow/issues/39)
- 선행 결정: [ADR-0002](0002-techflow-secret-lifecycle.md), [ADR-0003](0003-techflow-state-backup-recovery.md), [ADR-0004](0004-techflow-observability.md), [ADR-0006](0006-techflow-security-threat-model.md)
- 구조화 정책: [techflow-security-data-policy.json](../decisions/techflow-security-data-policy.json)

## 1. 결정

TechFlow는 데이터를 `D0 Public`, `D1 Internal`, `D2 Confidential`, `D3 Restricted`로 분류하고 생성·수집 시점에 등급, 소유자, 목적, 보존 정책과 파생 관계를 부여한다.

데이터는 정의된 업무 목적에 필요한 최소 범위로만 수집한다. 보존 기간은 삭제를 미루는 권리가 아니라 최대 기간이며, 목적 종료·동의 철회·Source 폐기·사고 대응에 따라 더 일찍 삭제할 수 있다. 법적·계약상 보존 요구는 별도 승인과 추적 ID가 있을 때만 일반 삭제를 일시 중단한다.

## 2. 데이터 등급

| 등급 | 정의 | 예 | 기본 처리 |
|---|---|---|---|
| `D0 Public` | 공개를 전제로 배포된 정보 | 공식 문서, 공개 릴리스, 공개 Issue | 출처·버전 유지, 공개 범위 내 검색 허용 |
| `D1 Internal` | 사내 업무용이며 공개가 승인되지 않은 정보 | 정규화 이벤트, 운영 메타데이터, 승인된 내부 문서 | 인증된 사용자, 목적 제한, 기본 90일 이하 |
| `D2 Confidential` | 개인정보·고객·지원·계약·민감 운영 정보 | 원문 AI 대화, 익명화 전 지원 사례 | 명시 승인, 암호화, 최소 30일, P1 RAG 금지 |
| `D3 Restricted` | 노출 시 즉시 권한 획득·중대한 피해가 가능한 정보 | 비밀번호, Token, Secret, 개인키, 원문 인증 Header | 일반 DB·로그·RAG·Prompt·Issue 저장 금지 |

분류가 불명확하면 한 단계 높은 등급을 적용하고 데이터 소유자가 재분류한다. 한 객체에 여러 등급이 섞이면 가장 높은 등급을 적용한다.

## 3. 공통 처리 규칙

모든 영속 데이터에는 가능한 범위에서 다음 메타데이터를 둔다.

```text
dataId, classification, owner, purpose
sourceId, sourceVersion, sourceUri
createdAt, updatedAt, expiresAt
retentionPolicyId, deletionState
parentDataIds, legalHoldId
tenantId, accessScope, correlationId
```

- `D1` 이상은 공개 Issue·PR·일반 Artifact에 원문을 포함하지 않는다.
- `D2`는 업무 목적·소유자·접근자·보존 기간을 명시적으로 승인해야 수집할 수 있다.
- `D3`는 ADR-0002의 보호 Secret 저장소 또는 제공자 권위 시스템에서만 처리한다.
- 분석·평가 데이터는 원본을 복사하지 않고 필요한 필드만 익명화·정규화한다.
- 로그·메트릭은 Payload가 아니라 상태, 개수, 시간, 허용된 오류 코드와 상관 ID만 기록한다.
- 데이터 Export는 원본 등급을 상속하며 낮은 등급 저장소로 이동할 수 없다.

## 4. 데이터 유형별 보존 기준

| 정책 ID | 데이터 | 등급 | 최대 보존 | 삭제·예외 |
|---|---|---|---:|---|
| R01 | 원문 Webhook Body·인증 Header | D2/D3 | `0일` | 검증 중 메모리 처리 후 즉시 폐기 |
| R02 | 정규화 이벤트·Delivery 메타데이터 | D1 | `90일` | 중복 키는 현재 구현 기준 7일 |
| R03 | Activepieces Flow Run 메타데이터 | D1 | `90일` | 입력·출력 원문은 수집 금지 또는 별도 등급 적용 |
| R04 | Gateway·App·Worker 구조화 로그 | D1 | `30일` | 현재는 서비스별 10MB×3 회전 한도도 함께 적용 |
| R05 | Observer 상태·경보 이력 | D1 | `90일` | 현재 상태 파일은 덮어쓰기, 외부 공유는 요약만 |
| R06 | 제품 감사 이벤트 | D1 | `365일` | 변경 작업 도입 시 변조 방지 저장소 필요 |
| R07 | PostgreSQL·Redis 정기 백업 | D1 | `7일` | ADR-0003 유지 |
| R08 | 명시적 복구 훈련 백업 | D1 | `30일` | ADR-0003 유지, 격리 복구 후 임시 자원 제거 |
| R09 | Secret Escrow | D3 | 대체본 검증 후 `30일 이내` | Bundle·Passphrase 분리, 일반 백업 제외 |
| R10 | 공개 지식 원문·현재 Chunk·Embedding | D0 | Source 사용 기간 | Source 철회·교체 후 7일 내 파생 데이터 삭제 |
| R11 | 공개 지식 이전 버전 | D0 | `365일` | 평가 재현용, 현재 검색에서는 제외 |
| R12 | 승인된 내부 지식·Embedding | D1 | 승인 기간, 최대 `365일` | 분기 재승인, P1은 기본 비활성 |
| R13 | AI Prompt·응답 원문 | D2 | 기본 미수집, 승인 시 최대 `30일` | 평가 반영 후 익명화하거나 삭제 |
| R14 | 익명화·승인된 평가 질문·답변 | D1 | `365일` | 원문 연결 정보 제거, 분기 품질 검토 |
| R15 | 익명화된 지원 해결 사례 | D1 | `180일` | 고객·사용자 재식별 가능 필드 제거 |
| R16 | 모델 사용량·비용·지연 메트릭 | D1 | `365일` | Prompt·응답·사용자 원문 제외 |
| R17 | 고객 원본 Export·디버그 Bundle | D2 | P1 수집 금지 | 향후 R2 승인·전용 저장소·만료 필요 |
| R18 | 비밀번호·Token·API Key·개인키 | D3 | 일반 저장 `0일` | 보호 저장소와 발급자 수명주기만 사용 |

보존 작업이 아직 자동화되지 않은 유형은 실제 원문 수집을 시작할 수 없다. Issue #20은 삭제 전파와 만료 검증이 준비되기 전 `D0`만 수집한다.

## 5. AI/RAG 데이터 정책

### 수집 허용

| 단계 | 허용 | 조건 |
|---|---|---|
| P1 기본 | D0 공식 공개 문서 | Source Allowlist, 소유자, 제품·버전, Hash |
| P1 조건부 | D1 승인 내부 문서 | 문서 소유자, 접근 범위, 만료일, 삭제 담당자 |
| P1 금지 | D2·D3, 고객 원본, 인증정보 | 색인·Embedding·Prompt 전송 모두 금지 |

### 파생 데이터

- Chunk와 Embedding은 원문 등급, Source ID, Version과 삭제 기한을 상속한다.
- Embedding은 익명 데이터로 간주하지 않는다.
- 현재 Source에서 제외된 Version은 검색 후보에서 즉시 제거한다.
- Source 삭제 요청은 Chunk, Embedding, Cache와 평가 데이터의 연결 항목까지 전파한다.
- AI Provider가 입력을 학습·장기 보존하는 구성은 별도 제품 책임자와 보안 검토 없이 사용할 수 없다.

### 답변과 평가

- 답변에는 사용한 Source와 Version을 기록한다.
- Prompt·응답 원문 수집은 기본 비활성이다.
- 품질 평가에는 익명화된 질문, 검색된 Source ID, 평가 점수와 승인자 수정 유형만 남긴다.
- 담당자 수정 내용에 개인정보·Secret이 포함되면 평가 데이터로 승격하지 않는다.

## 6. 삭제와 파생 데이터 전파

삭제 상태는 다음 수명주기를 사용한다.

```text
ACTIVE -> EXPIRING -> DELETION_REQUESTED -> DELETED
       -> LEGAL_HOLD -> DELETION_REQUESTED
```

삭제 작업은 다음 순서로 수행한다.

1. 원본을 신규 검색·Flow 입력에서 즉시 제외한다.
2. Source ID로 Chunk, Embedding, Cache와 평가 연결을 찾는다.
3. 운영 Primary와 검색 Index에서 최대 7일 이내 삭제한다.
4. 삭제 개수와 시간만 감사 기록으로 남긴다.
5. 백업은 복구 시 삭제 Ledger를 재적용하고 R07·R08 만료에 따라 자연 폐기한다.
6. 완료되지 않은 파생 삭제가 있으면 `DELETION_INCOMPLETE` 경보를 남긴다.

복구 환경에서 만료·삭제된 데이터가 다시 나타나면 외부 연결 전에 삭제 Ledger를 적용해야 한다.

## 7. Legal Hold와 예외

Legal Hold는 제품 책임자와 보안 책임자의 승인을 모두 받고 다음을 기록한다.

- `legalHoldId`, 사유와 법적·계약 근거
- 대상 데이터 ID·등급·기간
- 요청자·승인자와 적용·해제 시각
- 90일 이하의 다음 검토일

Legal Hold는 접근 통제·암호화·공유 금지를 해제하지 않는다. 종료되면 원래 만료일이 지난 데이터부터 삭제한다.

## 8. 책임

| 역할 | 책임 |
|---|---|
| 제품 책임자 | 데이터 목적·위험 허용·보존 기준·Provider 사용 승인 |
| 데이터 소유자 | Source 등급, 접근자, 정확성, 만료와 삭제 요청 |
| 보안 책임자 | D2·D3 처리, Legal Hold, 위협·사고 검토 |
| TechFlow Core | 분류·정책·Lineage·삭제 Ledger와 감사 원장 |
| Activepieces | 최소 이벤트 실행과 Run 이력, 제품 데이터 정책 결정 금지 |
| AI/RAG Gateway | 수집 Gate, ACL 검색, 출처·버전, Prompt·평가 최소화 |
| 운영자 | 백업·로그 회전·삭제 Job·복구 후 재삭제 검증 |

## 9. 정책 검증

- 모든 데이터 유형에 등급, 목적, 최대 보존과 삭제 방법이 있다.
- D3는 일반 로그·DB·RAG·Prompt·Issue·Artifact에서 0건이다.
- 원문 Webhook과 인증 Header는 영속 저장되지 않는다.
- D2·D3 문서가 P1 RAG에 들어가지 않는다.
- Source 철회 뒤 7일 내 Chunk·Embedding·Cache가 삭제된다.
- 만료 작업은 삭제 건수와 실패 건수만 기록한다.
- 상태 백업 7일·훈련 백업 30일이 유지된다.
- 복구 뒤 삭제 Ledger 재적용을 검증한다.
- Legal Hold는 이중 승인과 90일 이내 재검토일을 가진다.

## 10. 후속 구현

Issue #20에서 다음을 구현해야 한다.

- Source Registry와 문서 등급·소유자·Version·Hash
- Quarantine·승인·색인 상태
- Chunk·Embedding Lineage
- 만료·삭제 Job과 7일 SLO 검증
- Provider 데이터 처리 설정과 Prompt 원문 기본 미수집
- D0/D1 검색 ACL과 D2/D3 차단 테스트

Issue #23은 보존 위반, 삭제 지연, 비허용 등급 수집 건수를 KPI에 포함한다. Issue #24는 삭제 Job 실패와 데이터 수명주기 장애를 재처리·담당자 알림 범위에 포함한다.

## 11. 해석 한계

이 정책은 TechFlow 제품의 기술 기본값이다. 고객 계약, 개인정보보호법, 산업 규제 또는 법적 보존 의무가 더 엄격하면 해당 요구가 우선하며 별도 승인 정책으로 기록한다. 법적 판단을 Flow나 AI가 자동 추정하지 않는다.
