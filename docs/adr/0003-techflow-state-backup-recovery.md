# ADR-0003: TechFlow 상태 백업과 복구 기준

- 상태: 승인
- 결정일: 2026-07-31
- 적용 이슈: [#16 PostgreSQL·Redis 백업과 복구 검증](https://github.com/ablecloud-team/ablestack-techflow/issues/16)
- 선행 결정: [ADR-0001](0001-techflow-activepieces-responsibility-boundary.md), [ADR-0002](0002-techflow-secret-lifecycle.md)

## 1. 결정

TechFlow 테스트 환경의 복구 원본은 PostgreSQL 논리 백업과 Redis RDB 스냅샷으로 구성한다. 백업은 운영 컨테이너를 정지하지 않고 생성하며, 복구 검증은 운영 Compose 프로젝트와 분리된 Docker 네트워크·볼륨·컨테이너에서 수행한다.

| 항목 | 결정 |
|---|---|
| PostgreSQL | `pg_dump --format=custom`, Owner·Privilege 제외 |
| Redis | 인증된 `redis-cli --rdb` 스냅샷, RDB 무결성 확인 |
| 백업 주기 | 매일 `02:30 UTC`, 최대 10분 무작위 지연 |
| 보존 | 정기 백업 7일, 명시적 복구 훈련 백업 30일 |
| 저장 위치 | `/var/backups/ablestack-techflow/state`, `root:ablecloud 0750` |
| Archive 권한 | `root:ablecloud 0640` |
| 복구 훈련 | 내부 전용 네트워크, 공개 포트 0개, 임시 자원 자동 정리 |
| 복구 증적 | `/var/log/ablestack-techflow/recovery-drills`, 실제 값 없는 JSON |
| Secret | 상태 Archive에서 제외, 별도 암호화 Escrow와 별도 Passphrase |

## 2. 일관성 경계

PostgreSQL Dump는 하나의 논리적으로 일관된 데이터베이스 스냅샷이다. Redis RDB는 RDB가 생성된 시점의 일관된 스냅샷이다. 두 저장소의 스냅샷은 분산 트랜잭션으로 묶이지 않으므로 정확히 동일한 시점을 보장하지 않는다.

TechFlow는 영속 업무 상태의 원장을 PostgreSQL에 두고 Redis를 Queue·Lock·중복 방지 등 단기 상태로 제한한다. PostgreSQL과 Redis 사이의 재구성 불가능한 업무 원장을 이중 기록하지 않는다. 교차 저장소 원자성이 필요한 기능은 TechFlow Core에서 보상·재처리 가능한 상태 모델을 사용한다.

## 3. RPO와 RTO

| 구분 | M0 기준 | 판정 |
|---|---|---|
| RPO | 정기 백업 기준 24시간 + 최대 10분 지연 이내 | Timer 정책으로 충족 |
| RTO | 단일 서버 격리 복구 15분 이내 | 40초로 충족 |
| 백업 생성 | 운영 서비스 중단 없음 | 운영 컨테이너 ID 유지로 충족 |
| 복구 안전성 | 운영 Volume·Network·Port 미사용 | 격리 자원과 정리 결과로 충족 |

이 수치는 현재 약 197MiB PostgreSQL 데이터베이스와 소규모 Redis 상태에 대한 M0 실측값이다. 고객 환경의 RTO·RPO를 보장하지 않으며 데이터 규모별 부하·복구 시험을 별도로 수행해야 한다.

## 4. 무결성과 성공 판정

백업 성공은 다음 조건을 모두 만족할 때만 인정한다.

1. PostgreSQL Custom Dump와 Redis RDB가 생성된다.
2. Manifest의 파일 크기와 SHA-256이 일치한다.
3. Archive 내부의 `checksums.sha256`이 일치한다.
4. `.env`, 보호된 Secret 저장소와 Secret 감사 로그가 포함되지 않는다.
5. Archive 권한과 보존 위치가 기준에 맞는다.

복구 성공은 다음 조건을 모두 만족할 때만 인정한다.

1. PostgreSQL Dump가 새 Volume에 오류 없이 복원된다.
2. Public Table 수가 Manifest와 일치한다.
3. Redis RDB 자체 무결성 검사와 기동이 성공한다.
4. 양쪽 저장소의 복구 Probe가 모두 일치한다.
5. 공개 포트가 없고 운영 컨테이너 ID가 바뀌지 않는다.
6. 복구 후 운영 Health가 정상이다.
7. 임시 Container·Network·Volume·평문 파일이 제거된다.

Redis의 Source 관측 Key 수는 RDB 생성 직후에도 실행 중인 Queue 처리로 변할 수 있으므로 완전 일치 조건으로 사용하지 않는다. RDB 무결성, 정상 로드와 Snapshot 내부 Probe 일치를 성공 판정으로 사용한다.

## 5. Secret 복구 경계

PostgreSQL 백업에는 Activepieces가 암호화한 연결 데이터가 포함될 수 있으므로 원래 `AP_ENCRYPTION_KEY` 없이는 완전한 서비스 복구가 불가능하다. 그러나 상태 Archive에 Secret 파일을 함께 넣으면 하나의 유출로 데이터와 복호화 Root가 동시에 노출된다.

따라서 Secret은 다음처럼 분리한다.

- 상태 Archive는 Secret 원문을 포함하지 않는다.
- Secret 저장소는 OpenPGP AES-256 대칭 암호화 Escrow로 별도 생성할 수 있다.
- Passphrase는 Bundle과 같은 위치에 저장하지 않는다.
- 복구 훈련은 보호 파일을 교체하지 않고 격리된 임시 파일로 복호화한 뒤 Fingerprint와 필수 Key만 확인한다.
- 고객 Beta·GA에서는 암호화 Bundle과 Passphrase를 서로 다른 장애 영역의 승인된 외부 Vault에 보관한다.

M0 테스트 서버에서는 임시 Passphrase와 임시 암호화 Bundle로 절차를 실증한 뒤 모두 제거했다. 실제 외부 Vault 연결은 고객 배포 설계의 필수 조건이며 현재 서버의 로컬 백업만으로 Host 상실을 보호한다고 주장하지 않는다.

## 6. 장애 처리

- 백업 실패 시 부분 Archive를 남기지 않고 다음 Timer 실행 전 운영자에게 알릴 수 있는 실패 상태를 남긴다.
- 복구 실패 시 운영 환경으로 승격하지 않고 격리 자원을 기본적으로 정리한다.
- 장애 분석이 필요한 경우에만 `--keep-failed`로 격리 자원을 보존하고 수동으로 제거한다.
- Checksum 불일치, 안전하지 않은 Archive 경로 또는 Secret 파일 포함은 즉시 실패한다.
- 운영 Volume 복사, 덮어쓰기와 `docker compose down -v`는 자동 복구 절차에 포함하지 않는다.

로그·메트릭과 백업 실패 알림은 Issue #17에서 공통 운영 관측 체계에 연결한다.

## 7. 대안

| 대안 | 판단 |
|---|---|
| Docker Volume 전체 복사 | 실행 중 파일 일관성, 버전 이식성과 검증이 약해 채택하지 않음 |
| 운영 Volume에 직접 복원 | 실증 중 운영 데이터 훼손 위험 때문에 금지 |
| Redis AOF만 복사 | Redis 7 Multi-part AOF와 실행 중 복사의 복잡성 때문에 이식 가능한 RDB를 채택 |
| Secret을 상태 Archive에 포함 | 유출 반경이 커지므로 분리 |
| 즉시 외부 Backup 제품 도입 | M0 단일 서버 실증에는 과도하며 Provider 연결 전 절차와 인터페이스를 먼저 검증 |

## 8. 구현 완료 기준

- 정기 백업 Timer가 설치·활성화되고 실제 1회 실행에 성공한다.
- PostgreSQL·Redis 복구 Probe가 포함된 Archive를 생성한다.
- 격리 복구, RTO 측정, 운영 Health와 자원 정리를 검증한다.
- Secret Escrow의 암호화·격리 복호화 절차를 검증한다.
- Runbook, 구조화 증적, 보고서와 재현 가능한 생성 자산을 저장소에서 관리한다.
