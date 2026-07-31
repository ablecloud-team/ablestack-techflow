# Issue #16 PostgreSQL·Redis 백업·복구 완료 보고서

## 1. 결론

TechFlow 테스트 서버의 PostgreSQL과 Redis 상태를 운영 중단 없이 백업하고 격리된 환경에 복원하는 표준 절차를 구현·검증했다.

2026-07-31 실제 서버에서 복구 Probe를 포함한 약 72MiB Archive를 생성해 별도 내부 Network·임시 Volume·임시 Container로 복원했다. PostgreSQL 80개 Table, Redis RDB 무결성과 양쪽 Probe가 모두 통과했으며 복구 소요시간은 40초였다. 운영 PostgreSQL·Redis Container ID는 바뀌지 않았고 전체 6개 서비스 Health와 외부 HTTPS `200`이 유지됐다.

## 2. 구현 결과

| 영역 | 결과 |
|---|---|
| PostgreSQL | Custom Format 논리 백업, Owner·Privilege 제외 |
| Redis | 인증된 RDB Snapshot, RDB 무결성 검사 |
| 무결성 | Manifest 파일 크기·SHA-256과 Archive Checksum |
| 정기 실행 | Systemd Timer 활성화, 실제 Service 1회 `success` |
| 보존 | 정기 7일, 명시적 복구 훈련 30일 |
| 격리 복구 | 내부 Network, 공개 Port 0개, 운영 Volume 미사용 |
| 성공 판정 | Table 수, RDB 로드, 양쪽 Probe, 운영 Health |
| 정리 | 임시 Container·Network·Volume·평문 0개 |
| Secret | 상태 Archive에서 제외, 별도 AES-256 Escrow 절차 검증 |
| 문서화 | ADR, 배포·백업·복구 Runbook, 구조화 증적과 보고 자산 |

## 3. 기준선

| 항목 | 확인 결과 |
|---|---|
| PostgreSQL | `14.19`, 데이터베이스 206,766,883 Bytes, Public Table 79개 |
| PostgreSQL Volume | 약 447MiB |
| Redis | `7.0.7`, 훈련 후 Key 48개 |
| Redis Volume | 약 3.1MiB |
| Redis Persistence | AOF 활성, 마지막 RDB 상태 `ok` |
| Host 여유 공간 | 약 34GiB |
| 상태 Archive | 약 75.4MB, `root:ablecloud 0640` |

수치는 검증 시점의 관측값이며 장기 용량 계획 기준이 아니다.

## 4. RPO·RTO

| 지표 | 기준 | 실증 | 판정 |
|---|---|---|---|
| RPO | 정기 24시간 + 최대 10분 지연 | Timer 활성·실행 성공 | PASS |
| RTO | 15분 이내 | 40초 | PASS |
| 운영 중단 | 없음 | Container ID 유지 | PASS |
| 공개 면적 | 복구 Port 0개 | 0개 | PASS |

PostgreSQL과 Redis는 각각 일관된 Snapshot이지만 둘을 하나의 분산 트랜잭션 시점으로 묶지 않는다. 따라서 영속 업무 원장은 PostgreSQL에 두고 Redis 상태는 재구성·재처리 가능해야 한다.

## 5. 검증 결과

| ID | 검증 | 결과 |
|---|---|---|
| V1 | PostgreSQL Custom Dump 생성 | PASS |
| V2 | Redis RDB 생성·무결성 | PASS |
| V3 | Manifest·SHA-256 | PASS |
| V4 | `.env`·Secret 저장소·감사 로그 제외 | PASS |
| V5 | Systemd Timer 설치·실제 1회 실행 | PASS |
| V6 | 격리 PostgreSQL 복원 | 80 Table, Probe PASS |
| V7 | 격리 Redis 복원 | RDB·Probe PASS |
| V8 | 공개 Port | 0개 |
| V9 | 운영 Container ID | 변경 없음 |
| V10 | 운영 6개 서비스 Health | PASS |
| V11 | 외부 HTTPS | `200` |
| V12 | 임시 Container·Network·Volume | 모두 0개 |
| V13 | Secret AES-256 Escrow·격리 복호화 | PASS |
| V14 | 보호된 운영 Secret 원본 | 변경 없음 |
| V15 | `.env` 포함 구형 Archive | 안전 삭제 |

Redis Source 관측 Key는 51개, 복원 RDB에는 48개였다. Activepieces Queue가 실행 중인 상태에서 RDB 생성과 Source 수 집계 사이에 상태가 바뀐 결과다. RDB 파일 자체 검사, 정상 로드와 Snapshot 안에 기록한 Probe가 모두 통과했으므로 복구 성공으로 판정했다. Source Key 수는 정보성 관측값이며 완전 일치 조건이 아니다.

## 6. 보안과 Secret 복구

상태 Archive에는 실제 Secret 파일이 없다. PostgreSQL 안의 Activepieces 암호화 데이터는 원래 암호화 Key가 필요하므로 Secret 복구본을 버리지 않되 데이터 Backup과 분리한다.

실제 보호 파일을 임시 OpenPGP AES-256 Bundle로 암호화하고 별도 임시 Passphrase로 격리 복호화했다. 필수 Key 존재와 Source Fingerprint 일치를 확인한 뒤 Passphrase, Bundle과 평문을 모두 제거했으며 운영 파일은 변경하지 않았다.

현재 테스트 서버에는 승인된 외부 Vault가 연결되지 않았다. 따라서 로컬 상태 Backup은 디스크·Host 전체 상실을 보호하지 않는다. 고객 Beta·GA의 필수 조건은 암호화 Bundle과 Passphrase를 서로 다른 외부 장애 영역에 보관하고 정기 복구 훈련을 수행하는 것이다. 이 제한은 M0 단일 서버 기능 실증의 완료를 막지 않지만 제품 복구 보장을 주장할 수 있는 조건은 아니다.

Issue #14에서 생성한 `.env` 포함 구형 사전 배포 Archive는 현재 복구 기준을 대체할 상태 Backup과 Secret Escrow 검증 완료 후 정확한 단일 파일을 확인해 안전 삭제했다. 값이 없는 Issue #15 사전 배포 Archive는 보존했다.

## 7. 장애 처리와 안전성

- 부분 Archive는 성공 파일명으로 승격하지 않는다.
- Checksum 불일치와 Secret 파일 포함은 즉시 실패한다.
- 격리 복구는 운영 Compose, Volume과 Port를 사용하지 않는다.
- 실패 자원은 기본 정리하고 분석할 때만 명시적으로 보존한다.
- 운영 Volume 덮어쓰기와 자동 승격은 구현하지 않았다.
- 실제 장애 전환은 제품 책임자와 운영자의 별도 승인이 필요하다.

## 8. 자산

| 자산 | 역할 |
|---|---|
| ADR-0003 | Snapshot 경계, RPO·RTO, 성공 판정과 Secret 분리 |
| `backup-state.sh` | PostgreSQL·Redis Backup과 보존 |
| `restore-state-drill.sh` | 운영 비영향 격리 복구 |
| `test-backup-recovery.sh` | Probe·Backup·Restore·Health 통합 검증 |
| Systemd Service·Timer | 매일 정기 실행 |
| `verify-backup.sh` | 최신 Archive 권한·Checksum·Secret 제외 검증 |
| Secret Escrow Scripts | 별도 암호화 Backup과 격리 복호화 |
| Backup·Restore Runbook | 배포, 운영, 장애 복구와 보안 절차 |
| 구조화 JSON | 검증 기준과 결과의 기계 판독 증적 |

## 9. 완료 판정

Issue #16의 완료 기준인 백업 주기·보존·복구 절차·복구 시간 측정, 격리 복구 훈련, 테스트·운영 문서와 보안 영향 기록을 모두 충족했다.

다음 순서는 Issue #17 로그·메트릭·상태 점검 구성이다. 백업 Timer 실패, 최근 성공 시각, Archive 연령·용량과 복구 훈련 결과를 공통 운영 관측 체계에 연결한다.
