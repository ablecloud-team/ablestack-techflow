# Issue #62·#63 구현·검증 보고서

## 결과 요약

Diplo 현재 출시판과 Europa 미출시 프리뷰의 역할을 분리한 전 Source 기술지원 경로와 내부·외부 답변 분리를 구현했다. 일반 Chat 질문과 Community Draft는 사용자용 안전 Projection만 제공하고 승인 담당자의 Chat 상세에는 8개 Source Coverage와 코드 Citation을 제공한다.

AI Gateway `0.11.1`은 공개 답변을 `증상·원인·해결 방법·추가 고려사항·적용 버전` 순서의 트러블슈팅 문서로 표준화한다. Ubuntu 24.04 시험 서버 검증에서도 내부 Evidence Ledger와 외부 문서 분리, 8개 Source Coverage, Diplo 현재판과 Europa Preview 격리 원칙을 그대로 유지한다.

## 구현 자산

- `app/versioned_assist.py`: Source 역할, 전체 검토, 관련 근거 선별, Ledger, 안전 Projection
- `app/responses.py`: 현재판·프리뷰 구조화 Schema와 엄격한 프리뷰 정책
- `app/main.py`: 전 Source Assist, Community Draft, 일반 Chat Q&A
- `app/data/versioned-assist-golden-v1.json`: 6개 판정 Golden Case
- `tests/test_versioned_assist.py`: 역할·Coverage·Projection·Golden 계약 시험

## 최종 아키텍처

```mermaid
flowchart TB
    U["사용자 질문"] --> G["TechFlow AI Gateway 0.11.1"]
    G --> D["Docs"]
    G --> C["Diplo Current"]
    G --> O["5 Related Products"]
    G --> E["Europa Preview"]
    D --> X["Relevant Evidence Synthesis"]
    C --> X
    O --> X
    E --> X
    X --> R["OpenAI Structured Assessment"]
    R --> P["Safe Public Projection"]
    R --> L["Internal Evidence Ledger"]
    P --> CH["General Chat"]
    P --> CO["Community Draft"]
    L --> RV["Reviewer Chat Detail"]
```

## 자동 시험

| 항목 | 결과 |
|---|---:|
| Python Unit/Contract Test | 159 PASS |
| OpenAPI Operation | 33 |
| Versioned Golden Case | 6 |
| 현재 오류·프리뷰 개선 Case | 포함 |
| 현재 오류·프리뷰 미확인 Case | 포함 |
| 외부 Projection 내부 계보 검사 | PASS |
| `github-chat-v1` 동결 가드 | PASS |

## 시험 서버 배포

| 항목 | 최종 값 |
|---|---|
| OS | Ubuntu 24.04 |
| Root Volume | 1005 GiB, 사용 28 GiB, 여유 936 GiB |
| AI Gateway Image | `techflow/ai-gateway:issue-63-troubleshooting` |
| Gateway Version | `0.11.1` |
| Database / Vector | ready / ready |
| Provider | OpenAI |
| Gateway / Community Poller | healthy / running |
| 최종 백업 | `/home/ablecloud/techflow-ai-gateway-backups/troubleshooting-predeploy-20260812T104416Z` |

기존 0.11.0 배포 전 백업도 `/home/ablecloud/techflow-ai-gateway-backups/issue62-predeploy-20260812T095938Z`에 보존되어 있다.

Secret 파일과 값은 복사·출력·문서화하지 않았다. Database Migration은 없으며 기존 `source_metadata` JSON에 Evidence Ledger를 저장한다.

## E2E 결과

### E2E 0: 트러블슈팅 문서 형식

- Gateway: `0.11.1`, Image `techflow/ai-gateway:issue-63-troubleshooting`
- 일반 Chat: `ANSWERED`, 1,881자, 필수 Section 5개 순서 검증 PASS
- Community Discussion: [#151](https://community.ablecloud.io/d/151)
- Community Case: `9be04737...`, `DRAFT_PENDING / ANSWERED`
- Community Draft: 1,806자, 필수 Section 5개 순서 검증 PASS
- Coverage: 8개, 내부 Citation: 4개
- 외부 저장소·Profile·Commit·경로·라인 노출: 0건
- `증상 → 원인 → 해결 방법 → 추가 고려사항 → 적용 버전` 순서를 Chat과 Community에서 동일하게 확인
- 자동 게시·승인: 수행하지 않음

### E2E 1: 범용 질문 보류

- 질문: Diplo 환경의 일반적인 VM 배포 실패 원인과 Europa 개선 여부
- 전체 Coverage: 8개 Profile 검색 수행
- 결과: `ABSTAINED`
- 현재판: `INSUFFICIENT_EVIDENCE`
- 프리뷰: `PREVIEW_INSUFFICIENT`
- 판정: 환경·로그 없이 원인을 확정하지 않아 PASS

### E2E 2: 일반 Chat 답변

- 질문: Diplo `StorageServiceHostCommand` 주요 필드와 Europa 관련 변경
- 결과: `ANSWERED`, 안전 Projection 1,612자
- 내부 경로·Profile·GitHub URL 노출: 0건
- Reviewer 권한이 없는 유효 Chat 사용자 기술 질문: 허용
- 판정: PASS

### E2E 3: Community 최종 Case

- Discussion: [#150](https://community.ablecloud.io/d/150)
- Case: `c6729fa1...`
- 상태: `DRAFT_PENDING / ANSWERED`
- Draft: 1,810자
- 내부 Citation: 4개
- Coverage: 8개
- 공개 Draft 금지 패턴: 0건
- 자동 게시: 수행하지 않음. 담당자 승인 대기
- 판정: PASS

### E2E 4: Reviewer Chat 상세

| Profile | 역할 | 최종 관련 근거 |
|---|---|---:|
| SHARED_DOCS | 현재 문서 | 0 |
| CLOUD_DIPLO | 현재 출시 Cloud | 2 |
| WALL_MAIN | 현재 연관 제품 | 0 |
| COCKPIT_DIPLO | 현재 연관 제품 | 0 |
| GENIE_MASTER | 현재 연관 제품 | 0 |
| KICKSTART_MASTER | 현재 연관 제품 | 0 |
| QEMU_EXEC_TOOLS_MAIN | 현재 연관 제품 | 0 |
| CLOUD_EUROPA | 미출시 프리뷰 | 2 |

Reviewer 상세에는 Commit·파일·라인 Citation 4개와 `CURRENT_NORMAL / PREVIEW_NOT_FOUND`가 표시됐다. 일반 사용자 답변에는 같은 계보가 표시되지 않았다.

## 구현 중 발견과 개선

첫 구현은 8개 Profile의 벡터 상위 결과를 모두 생성 컨텍스트에 넣어 직접 관련 없는 근거 때문에 정확한 코드 질문도 보류됐다. 검색 수행과 생성 근거 사용을 분리하고, 질문에 명시적 코드 식별자가 있으면 해당 식별자와 직접 일치하는 결과만 채택하도록 수정했다. 이후 Diplo·Europa 각각 2개 근거만 사용해 Chat과 Community 답변이 정상 생성됐다.

## 기존 서비스 보호

`protected_service=github-chat-v1 state=frozen guard=passed`를 확인했다. 실제 `techflow-activepieces-event-gateway-1`은 기존 `ablestack-techflow/event-gateway:0.4.0` Image로 2일 이상 재시작 없이 `healthy`였으며 이번 Gateway 배포 대상에 포함하지 않았다.

## 완료 판정

Issue #62의 전 Source 검토·Diplo/Europa 비교와 Issue #63의 내부 Ledger·외부 Projection 분리 완료 기준을 충족했다. 사용자 답변은 5개 Section의 트러블슈팅 문서로 표준화했으며 PR #61은 Ready 상태를 유지한다.
