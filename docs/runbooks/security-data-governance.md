# TechFlow 보안 위협·데이터 수명주기 운영 Runbook

> 적용 기준: [ADR-0006](../adr/0006-techflow-security-threat-model.md), [ADR-0007](../adr/0007-techflow-data-classification-retention.md)
>
> 구조화 정책: [techflow-security-data-policy.json](../decisions/techflow-security-data-policy.json)
>
> 적용 이슈: [#39](https://github.com/ablecloud-team/ablestack-techflow/issues/39)

## 1. 목적

새 Integration, Flow, 데이터 저장소, AI Provider와 지식 Source를 추가할 때 위협과 데이터 수명주기를 같은 절차로 검토한다. 이 Runbook은 실제 비밀정보나 데이터 원문이 아니라 정책 ID, 등급, 소유자, 기간과 검증 결과만 기록한다.

## 2. 변경 전 분류

새 데이터 유형마다 다음 질문에 답한다.

| 질문 | 필수 기록 |
|---|---|
| 어떤 업무 목적에 필요한가 | 단일 목적과 기능 Issue |
| 데이터 소유자는 누구인가 | 역할 또는 승인된 담당자 |
| 공개 여부와 피해는 무엇인가 | D0·D1·D2·D3 |
| 원문이 꼭 필요한가 | 최소 필드와 원문 미수집 근거 |
| 어디에 저장·전송되는가 | Primary, Log, Backup, Provider, Export |
| 무엇이 파생되는가 | Chunk, Embedding, Cache, 평가 데이터 |
| 언제 어떻게 삭제하는가 | Retention Policy ID, Job, SLO |
| 누가 접근·승인하는가 | Scope, 승인자, 감사 ID |

분류가 불명확하면 높은 등급을 적용한다. `D2`와 `D3`는 보안 책임자 검토 전 구현 데이터를 수집하지 않는다.

## 3. 위협 모델 갱신

새 경계나 자산이 추가되면 구조화 정책의 `assets`, `trustBoundaries`, `controls`, `threats`를 갱신한다.

1. 공격자가 통과하는 신뢰 경계를 식별한다.
2. 기밀성·무결성·가용성·권한·안전 영향을 기록한다.
3. 가능성·영향을 1~5로 산정한다.
4. Flow 설명이 아닌 강제 계층의 Control을 연결한다.
5. 실패·우회·경계 테스트를 정의한다.
6. 잔여 위험을 다시 계산한다.

잔여 점수가 10 이상이면 배포하지 않는다. 통제를 구현하거나 기능·데이터 범위를 줄인 뒤 다시 평가한다.

## 4. 정책 자동 검증

```bash
python3 tools/policy/validate_security_data_policy.py \
  docs/decisions/techflow-security-data-policy.json

python3 -m unittest -v \
  tools.policy.test_validate_security_data_policy
```

정상 출력은 다음 조건을 만족한다.

```text
policy=valid threats=18 controls=28 classifications=4 retention=18
Ran 12 tests
OK
```

검증기는 참조 무결성, 잔여 위험, D3 기본 수집 금지, 보존 상한, RAG 등급 Gate, 7일 삭제 SLO와 Legal Hold 이중 승인을 검사한다.

## 5. AI/RAG Source 등록

Issue #20에서 Source Registry를 구현하기 전에는 `D0`만 실제 수집한다. Source 등록에는 다음 필드가 필요하다.

```text
sourceId, owner, classification
product, version, sourceUri
contentHash, collectedAt
retentionPolicyId, accessScope
```

수집 순서:

1. Source URI가 승인된 공식 목록에 있는지 확인한다.
2. D0·D1 등급과 소유자·접근 범위를 확정한다.
3. 문서를 `QUARANTINED` 상태로 수집한다.
4. Secret·개인정보·악성 지시·스크립트·숨은 콘텐츠를 검사한다.
5. 제품·버전·Hash와 이전 Version 관계를 기록한다.
6. 승인 후에만 `INDEXED`로 전환한다.
7. Chunk·Embedding에 Source ID·Version·등급·삭제 기한을 상속한다.

다음 자료는 P1 수집 금지다.

- 비밀번호, Token, API Key, 개인키와 인증 Header
- 고객 원본 Export와 익명화되지 않은 지원 Bundle
- 원문 AI 대화와 개인정보가 포함된 지원 사례
- 소유자·출처·버전·Hash를 확인할 수 없는 문서
- 문서 안의 지시를 System Policy로 실행하도록 요구하는 데이터

## 6. AI Provider 승인

Provider 연결 전 다음을 확인한다.

- Prompt·응답의 저장 기간과 학습 사용 여부
- 데이터 처리 지역과 하위 처리자
- 삭제·비활성화 방법과 계약 변경 통보
- 모델·API Version과 비용·Rate Limit
- Timeout·429·5xx·응답 유실의 판정
- D2·D3가 전송되지 않는 기술적 차단

승인되지 않은 Provider에는 실제 데이터를 전송하지 않는다. 인증정보는 ADR-0002의 런타임 Secret 경로로만 주입한다.

## 7. 삭제 요청

삭제 요청에는 원문 대신 `dataId`, `sourceId`, 정책 ID와 사유 유형만 기록한다.

1. 대상을 신규 검색·실행에서 즉시 제외한다.
2. 상태를 `DELETION_REQUESTED`로 전환한다.
3. Source Lineage로 Chunk·Embedding·Cache·평가 연결을 찾는다.
4. Primary와 파생 저장소에서 최대 7일 이내 삭제한다.
5. 삭제 대상·성공·실패 개수와 완료 시각을 감사 기록으로 남긴다.
6. 실패가 남으면 `DELETION_INCOMPLETE` 경보와 재처리 작업을 생성한다.
7. 백업 복구 시 삭제 Ledger를 먼저 재적용한다.

Issue #20에 삭제 Job이 구현되기 전에는 수동 삭제가 필요한 D1 데이터도 수집하지 않는다.

## 8. 보존 만료 점검

월 1회 또는 새 데이터 유형 배포 후 다음을 검토한다.

- 만료 예정·만료 초과 데이터 개수
- 삭제 SLO 7일 초과 건수
- D2·D3가 일반 DB·로그·RAG에 존재하는지 여부
- Source가 철회됐지만 Index에 남은 Chunk 개수
- 상태 백업 7일·훈련 백업 30일 초과 Archive
- Raw AI Prompt·응답 수집이 기본 비활성인지 여부
- Legal Hold의 다음 검토일

현재 자동화되지 않은 점검은 값이 없는 집계 결과만 수동 증적으로 남긴다. Issue #23에서 KPI로, Issue #24에서 실패 재처리·알림으로 전환한다.

## 9. Legal Hold

Legal Hold는 제품 책임자와 보안 책임자의 이중 승인이 필요하다.

```text
legalHoldId, reason, basis
dataIds, classification
requestedBy, approvedBy
appliedAt, reviewAt
```

`reviewAt`은 적용일부터 90일을 넘을 수 없다. Hold 중에도 접근 통제와 외부 공유 금지는 유지한다. 해제 시 원래 만료일이 지난 데이터부터 삭제한다.

## 10. 보안 사고

| 사고 | 즉시 조치 | 복구 기준 |
|---|---|---|
| Secret 노출 | 발급자 폐기, 런타임 교체, 영향 경로 차단 | 이전 값 거부·서비스 정상·노출 0건 |
| Prompt Injection·지식 오염 | Source Quarantine, Index 제외 | 수정 Source 승인·파생 데이터 삭제 |
| 등급 간 검색 유출 | RAG 비활성화, ACL·등급 Gate 점검 | 교차 등급 테스트 통과 |
| Provider 오보존 | Provider 전송 중단, 계약·삭제 요청 | 삭제 증거·대체 Provider 승인 |
| 삭제 Job 실패 | 신규 수집 중단, 실패 대상 재처리 | 7일 SLO와 Lineage 일치 |
| 불명확한 자원 작업 | `UNKNOWN`, ABLESTACK 상태 재조회 | 권위 상태와 감사 기록 수렴 |

공개 저장소에는 취약점 재현 Payload, Secret, 내부 로그와 고객 데이터를 게시하지 않는다. 공개가 위험한 취약점은 비공개 Security Advisory를 사용한다.

## 11. 변경·롤백

정책 완화는 일반 코드 변경보다 높은 검토를 요구한다. 등급 하향, 보존 연장, D2 수집, 새 Provider와 AI Tool 실행 허용은 제품 책임자와 보안 책임자의 승인을 모두 받는다.

새 데이터 경로가 정책 검증 또는 E2E 격리 테스트에 실패하면 다음 순서로 롤백한다.

1. Source 수집·AI Provider 전송·Flow를 비활성화한다.
2. 신규 Index와 Cache를 Quarantine한다.
3. 직전 승인 정책과 Flow Version으로 복귀한다.
4. 신규 수집 데이터와 파생 데이터를 삭제한다.
5. 상태·백업·감사 원본은 승인된 보존 정책에 따라 유지한다.
6. 후속 Issue에서 원인과 통제 보완을 추적한다.

## 12. 정기 검토

- 분기: 데이터 등급, Source, Provider, Legal Hold, 평가 세트
- 반기: 위협 가능성·영향·잔여 위험과 Control 소유자
- 변경 시: 새 Integration, 모델, Piece, Domain Pack, 고객 데이터, 자원 변경 기능
- 사고 후: 실패한 Control, 탐지 지연, 삭제·폐기와 재발 방지
