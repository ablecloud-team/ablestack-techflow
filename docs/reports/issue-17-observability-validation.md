# Issue #17 로그·메트릭·상태 점검 완료 보고서

## 1. 결론

TechFlow 테스트 서버에 1분 주기의 경량 관측 수집기와 최소 경보 체계를 구현하고 실제 장애 감지·복구 훈련을 완료했다.

2026-07-31 UTC 기준 6개 Compose 서비스, 내부 App·Gateway와 외부 HTTPS Health, PostgreSQL, Redis, 상태 백업을 정상 수집했다. `event-gateway`를 잠시 중단한 훈련에서 수집기는 Critical 종료 코드 `2`, `service_event-gateway`와 `endpoint_internal_gateway` 원인을 기록했고 재시작 후 두 경보의 해제를 기록했다. systemd `OnFailure` 로컬 알림도 journal에 남는 것을 확인했다.

## 2. 구현 결과

| 영역 | 결과 |
|---|---|
| 수집 주기 | systemd Timer 1분, `enabled/active` |
| 상태 | JSON 스냅샷, 6/6 Healthy |
| 메트릭 | Prometheus Text Format 43 시계열 |
| 경보 | Warning·Critical 정책과 발생·해제 전이 |
| 로그 | Gateway 구조화 집계, App·Worker 오류 행 수 |
| 로그 용량 | 6개 서비스 모두 `local`, `10m × 3` |
| 장애 훈련 | Gateway 중단 감지, 원인 식별, 복구·해제 PASS |
| 보안 | 관측 자산 5개, Secret 6종 대조, 누출 0 |
| 운영 문서 | ADR-0004, 설치·점검·대응·훈련 Runbook |

## 3. 실서버 검증 기준선

검증 시각은 `2026-07-31T09:38:05Z`이며 운영 용량 계획을 보장하는 값이 아니라 해당 시점 관측값이다.

| 항목 | 관측값 |
|---|---:|
| Ubuntu | 24.04 |
| 루트 파일시스템 사용률 | 22.93% |
| 사용 가능 메모리 비율 | 69.18% |
| 서비스 Health | 6/6 |
| 내부 App / Gateway / 외부 App | HTTP 200 / 200 / 200 |
| PostgreSQL | 연결 2/100, DB 206,766,883 Bytes |
| Redis | Client 17, 거부 연결 0, RDB/AOF `ok/ok` |
| 최신 상태 백업 | 75,441,555 Bytes, 약 4분 이내 |
| 활성 경보 | Critical 0, Warning 0 |
| 관측 파일 권한 | 모두 `root:root 0640` |

Flow 실행 이력이 없어 상태별 실행 수와 24시간 지연 분포는 빈 시계열이었다. 수집기와 쿼리 경로는 단위 테스트로 검증했으며 실제 Flow 업무 검증은 후속 사내 자동화 Flow에서 데이터가 생성된 뒤 진행한다.

## 4. 장애 시나리오

| 단계 | 수행 | 결과 |
|---|---|---|
| 1 | 정상 상태 Strict 수집 | 경보 0, 종료 0 |
| 2 | 기존 `event-gateway` 컨테이너 Stop | 대상 한정 |
| 3 | Strict 수집 | 종료 2 |
| 4 | 현재 경보 확인 | 서비스·내부 Gateway 원인 식별 |
| 5 | systemd Service 실행 | 실패 Unit 및 `techflow-alert` journal 기록 |
| 6 | 같은 컨테이너 Start | 전체 Health 회복 |
| 7 | 재수집 | 두 경보 `resolved` |
| 8 | 최종 검증 | 6/6 Healthy, 외부 HTTPS 200 |

훈련 증적에는 Scenario, 기대·실제 종료 코드, 경보 키와 복구 결과만 저장했다. 요청 본문, Flow·사용자 식별자와 원문 로그는 저장하지 않았다.

## 5. 경보와 운영 추적성

수집기는 경보 상태 자체뿐 아니라 발생·해제 전이를 기록한다. 따라서 운영자는 다음 순서로 원인을 추적한다.

1. `techflow-observer status`에서 심각도와 컴포넌트를 확인한다.
2. `current-alerts.json`에서 고정 경보 키와 요약을 확인한다.
3. `alerts.jsonl`에서 발생·해제 시간을 확인한다.
4. Runbook의 컴포넌트별 안전한 진단 명령을 실행한다.
5. 복구 후 재수집해 같은 키가 해제되었는지 확인한다.

M0 알림 채널은 호스트의 JSONL과 systemd journal이다. 중앙 알림 수신처가 정해지지 않은 상태에서 임의 Webhook이나 개인 계정을 연결하지 않았다. Slack·메일·Pager는 수신 채널, 운영 시간과 에스컬레이션 책임자가 확정되면 경보 전이를 소비하는 Adapter로 추가한다.

## 6. 보안과 개인정보

- Observer는 `.env`에서 Bind, Port, Public URL, Backup 경로 네 항목만 Allowlist로 읽는다.
- PostgreSQL·Redis Secret은 호스트 명령행이나 관측 파일에 기록하지 않는다.
- Flow ID, 실패 Step, Payload, 사용자 정보와 원문 로그를 수집하지 않는다.
- 서비스·엔드포인트·상태처럼 제한된 Label만 메트릭에 사용한다.
- 상태·메트릭·경보 파일은 원자적으로 교체하고 `0640`으로 제한한다.
- 실서버 관측 자산을 런타임 Secret 6종과 대조한 결과 누출은 0건이었다.

## 7. 배포 과정 자산화

1. 변경 Compose와 Python·Shell 구문 및 단위 테스트를 사전 검증했다.
2. `pre-issue17-observability` 상태 백업을 생성했다.
3. Compose에 로그 보존 한도를 반영하고 6개 컨테이너를 재생성했다.
4. 6개 Health, Worker polling, 내부·외부 Endpoint를 확인했다.
5. Observer·systemd Unit·Timer를 설치하고 첫 정상 수집을 확인했다.
6. 장애 감지·systemd 알림·복구 훈련을 수행했다.
7. 전체 관측 자산 Secret Scan과 최종 Health를 재검증했다.

구체 명령과 장애 대응은 [관측성 운영 Runbook](../runbooks/observability.md)에 유지한다.

## 8. 완료 판정

| ID | 검증 | 결과 |
|---|---|---|
| V1 | Observer 단위 테스트 7건 | PASS |
| V2 | Timer enabled·active | PASS |
| V3 | 6개 서비스 Health | PASS |
| V4 | 내부 App·Gateway·외부 HTTPS 200 | PASS |
| V5 | PostgreSQL·Redis·Backup 수집 | PASS |
| V6 | Prometheus 형식 43 시계열 | PASS |
| V7 | Gateway 장애 Critical 감지·원인 식별 | PASS |
| V8 | 경보 발생·해제 전이 | PASS |
| V9 | systemd `OnFailure` journal 알림 | PASS |
| V10 | 장애 후 전체 Health·HTTPS 복구 | PASS |
| V11 | 6개 서비스 로그 보존 한도 | PASS |
| V12 | 파일 권한·Secret Scan | PASS |

Issue #17의 완료 기준인 장애 감지와 원인 추적, 테스트·운영 문서화, 보안 영향 반영을 모두 충족했다.

## 9. 제한과 다음 단계

현재 관측 파일은 단일 호스트에 있으며 장기 저장, 그래프 대시보드, 외부 알림을 제공하지 않는다. 다음 단계에서는 먼저 실제 사내 업무 Flow를 구성해 Flow 상태·지연 메트릭을 실증하고, 필요 시 중앙 수집과 알림 Adapter를 추가한다.

고객 공개 여부와 최종 제품화 범위는 제품 책임자의 별도 결정이며 본 구현의 범위나 완료 판정을 제한하지 않는다.
