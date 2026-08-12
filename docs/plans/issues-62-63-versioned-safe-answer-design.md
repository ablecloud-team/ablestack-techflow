# Issue #62·#63 Diplo 현재판·Europa 프리뷰 비교와 안전 답변 설계

## 목적

ABLESTACK 기술지원 질문마다 공개 문서, Diplo 현재 출시 Cloud, Wall, Cockpit, Genie, Kickstart, QEMU 실행 도구를 검토한다. 제품 자료만으로 설명되지 않는 하이퍼바이저 런타임 문제는 검토·승인된 QEMU/libvirt 공식 자료와 ABLESTACK 운영 지식의 로컬 스냅샷을 함께 사용한다. Europa 미출시 코드는 향후 개선 여부를 판단하는 프리뷰 근거로만 사용한다. 내부 담당자는 근거 계보 전체를 확인하지만 Community와 일반 Chat 사용자는 문제 해결에 필요한 내용만 받는다.

## 제품 버전 역할

| 역할 | Source Profile | 사용 원칙 |
|---|---|---|
| 현재 문서 | `SHARED_DOCS` | 현재 사용·운영 절차의 1차 근거 |
| 현재 출시 Cloud | `CLOUD_DIPLO` | 현재 동작·설정·결함 판정의 권위 근거 |
| 현재 연관 제품 | `WALL_MAIN`, `COCKPIT_DIPLO`, `GENIE_MASTER`, `KICKSTART_MASTER`, `QEMU_EXEC_TOOLS_MAIN` | 질문과 직접 연관될 때 통합 진단 근거 |
| 현재 플랫폼 참조 | `CURATED_PLATFORM_REFERENCE` | 승인된 운영 지식과 QEMU/libvirt 공식 문서의 로컬 스냅샷. 외부 실시간 조회 금지 |
| 미출시 프리뷰 | `CLOUD_EUROPA` | 같은 원인의 개선 여부 비교에만 사용 |
| 내부 참고 전용 | `CLOUD_MAIN` | 일반 사용자 답변 경로에서 제외 |

## 처리 흐름

```mermaid
flowchart LR
    Q["Community 또는 Chat 질문"] --> R["9개 근거 영역 독립 검토"]
    R --> C["질문 직접 관련 근거 선별"]
    C --> D["Diplo 현재판 판정"]
    C --> H["QEMU/libvirt 런타임 판정"]
    C --> E["Europa 프리뷰 비교"]
    D --> S["통합 Evidence Synthesis"]
    H --> S
    E --> S
    S --> L["내부 Evidence Ledger"]
    S --> P["사용자용 안전 Projection"]
    L --> V["승인 담당자 Chat 상세"]
    P --> U["일반 Chat 응답"]
    P --> A["Community 승인 대상 초안"]
```

각 Profile 검색은 독립 실행한다. 전체 검색 수행 자체와 최종 생성 컨텍스트 포함 여부를 구분한다. 벡터 검색 상위 결과를 무조건 결합하지 않고 질문의 식별자·핵심 용어와 직접 일치하는 근거만 생성 컨텍스트에 넣는다. `NO_RELEVANT_EVIDENCE`도 검토 완료 결과로 Ledger에 남긴다.

## 판정 계약

현재판 판정은 다음 중 하나다.

- `CURRENT_NORMAL`: 현재 문서와 Diplo 구현이 일치하고 정상 동작이다.
- `CURRENT_CONFIG_ERROR`: 설정·환경·운영 입력 문제 가능성이 높다.
- `CURRENT_DEFECT`: Diplo 현재 구현의 결함 가능성이 근거로 확인된다.
- `CURRENT_RUNTIME_ISSUE`: Diplo 제품 코드 결함이 아니라 QEMU/libvirt 등 가상화 런타임 상태 문제로 판단된다.
- `INSUFFICIENT_EVIDENCE`: 현재 상태를 확정할 근거가 부족하다.

Europa 프리뷰 비교는 다음 중 하나다.

- `PREVIEW_IMPROVED`: 동일 원인을 직접 해결하는 개선 근거가 있다.
- `PREVIEW_PARTIAL`: 일부 연관 개선은 있으나 완전한 해결은 확인되지 않는다.
- `PREVIEW_NOT_FOUND`: 직접 대응하는 개선을 확인하지 못했다.
- `PREVIEW_INSUFFICIENT`: 비교 근거가 부족하다.
- `NOT_APPLICABLE`: 현재 질문에 프리뷰 비교가 필요하지 않다.

`PREVIEW_IMPROVED`도 출시 확정, 출시 시점, 고객 제공 완료를 뜻하지 않는다. 명시적 Release Metadata가 없는 경우 “개선이 진행 중인 정황”으로만 안내한다.

## 내부 Ledger와 외부 Projection

내부 Ledger에는 정책 ID, 9개 근거 영역별 검토 상태·근거 수, 현재판·프리뷰 판정, Citation의 저장소·브랜치·커밋·파일·라인 또는 공식 참조 URL을 저장한다. Chat `상세 <Case>`는 답변만 표시하고, 승인 담당자가 `근거 <Case>`를 명시한 경우에만 Ledger를 표시한다.

외부 Projection은 다음 정보를 제거한다.

- GitHub URL과 저장소 소유자·이름
- Source Profile ID와 브랜치 이름
- Commit SHA, 파일 경로, 라인 번호, 내부 Evidence ID
- 답변에 불필요한 내부 토폴로지·스택 정보

Community는 안전 Projection만 Draft로 저장·게시하고 일반 Chat 질의도 같은 Projection을 사용한다. Reviewer 권한은 `상세`, `근거`, `승인`, `수정`, `반려`, `대기`, `이력` 명령에만 적용하며 일반 기술 질문은 유효한 Chat Bot 이벤트 사용자에게 제공한다.

Community Poller는 10초 간격으로 신규 미답변 Discussion을 감지한다. Case가 처음 생성되면 연결된 Reviewer에게 즉시 “새 Community 글” Chat 카드를 전송하고 실패 시 짧은 간격으로 최대 3회 재시도한다. 중복 Discussion/Idempotency 재처리에는 알림을 다시 보내지 않는다. 알림과 `상세`에는 질문·답변만 포함하며 근거는 포함하지 않는다.

## 승인된 외부 플랫폼 참조 계약

- 답변 시점에 인터넷을 실시간 탐색하지 않는다. `curated-platform-references-v1.json`의 승인된 로컬 스냅샷만 생성 근거로 사용한다.
- `OPERATOR_APPROVED_KNOWLEDGE`는 알려진 ABLESTACK 운영 증상의 원인·조치 기준이고, `OFFICIAL_EXTERNAL_DOCUMENTATION`은 QEMU/libvirt 동작 원리를 보강한다. 공식 문서만으로 개별 장애 원인을 확정하지 않는다.
- 30일마다 공식 URL의 변경 여부를 확인하되 Source Reviewer 승인 전에는 새 스냅샷을 활성화하지 않는다.
- 사용자 답변에는 참조 URL, 저장소, Commit, 내부 ID를 표시하지 않는다. 담당자가 Chat에서 `근거 <Case>`를 입력한 경우에만 내부 검토용으로 제공한다.
- CLI는 공급된 근거에 있는 명령만 사용한다. 조회 명령과 상태 변경 작업을 분리하고, `<VM>` 같은 Placeholder, 필요 권한, 서비스 영향, 비밀정보 금지를 함께 안내한다.
- ABLESTACK가 관리하는 가상머신의 마이그레이션·정지·시작은 Mold 또는 승인된 제품 API로 수행한다. 직접 `virsh migrate`는 관리 계층 상태를 우회할 수 있으므로 기본 안내에서 제외한다.

### 사용자용 트러블슈팅 문서 계약

외부 Projection은 항상 다음 순서를 유지한다.

1. **증상**: 질문 요약과 실제로 관찰된 현상
2. **원인**: 근거로 확인하거나 가능성을 판정한 원인
3. **해결 방법**: 현재 출시판에 적용할 확인·조치 절차
4. **추가 고려사항**: 아직 필요한 정보, 위험, Europa 개선 참고사항
5. **적용 버전**: Diplo 현재 출시판 판정과 Europa 미출시 Preview 판정을 명확히 분리

자료에 없는 정확한 제품 버전 번호나 출시 시점은 생성하지 않는다. 원인 또는 추가 고려사항이 비어 있어도 제목을 생략하지 않고 확인 상태를 명시해 문서 형식을 안정적으로 유지한다.

## Golden Set

`versioned-assist-golden-v1.json`은 다음 7개 판정 조합을 고정한다.

1. 현재 결함·프리뷰 개선
2. 현재 결함·프리뷰 일부 개선
3. 현재 결함·프리뷰 개선 미확인
4. 현재 설정 오류
5. 현재 정상
6. 현재·프리뷰 근거 부족
7. Mold 콘솔 `연결중`: QEMU VNC 세션/소켓 런타임 문제, 읽기 전용 CLI 확인, 라이브 마이그레이션 우선, 정지 후 시작 대안

각 Case는 외부 금지 주장도 함께 정의한다. Golden Set은 코드 단위 계약 검증에 사용하고 실서버 E2E는 실제 색인·OpenAI·Community·Chat 경로를 검증한다.

## 완료 기준

- 8개 제품 Profile과 1개 승인 플랫폼 참조 영역의 독립 검토 상태가 Ledger에 남는다.
- Diplo와 Europa 근거가 현재 동작 주장으로 혼합되지 않는다.
- Community와 일반 Chat 외부 답변의 내부 계보 노출이 0건이다.
- Reviewer Chat `상세`에는 답변만 보이고 `근거 <Case>`에서만 전체 Coverage와 Citation을 확인할 수 있다.
- 신규 미답변 Discussion은 최대 Poll 10초와 답변 생성 시간 뒤 Reviewer Chat으로 자동 알림되며 `대기` 명령에 의존하지 않는다.
- 현재 오류·개선·미개선 Golden Case가 자동 시험에 포함된다.
- 시험 서버 E2E와 기존 `github-chat-v1` 동결 가드가 통과한다.
