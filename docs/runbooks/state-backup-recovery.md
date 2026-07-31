# TechFlow 상태 백업·복구 Runbook

## 1. 목적

이 문서는 TechFlow 테스트 서버의 PostgreSQL·Redis 상태를 백업하고 운영 환경을 변경하지 않는 격리 복구 훈련을 수행하는 표준 절차다. 정책 기준은 [ADR-0003](../adr/0003-techflow-state-backup-recovery.md)이다.

## 2. 경로와 권한

| 경로 | 권한 | 용도 |
|---|---|---|
| `/opt/ablestack-techflow/activepieces` | `ablecloud` 운영 경로 | Compose와 백업·복구 스크립트 |
| `/var/backups/ablestack-techflow/state` | `root:ablecloud 0750` | PostgreSQL·Redis Archive |
| `techflow-state-*.tar.gz` | `root:ablecloud 0640` | 상태 Backup |
| `/var/backups/ablestack-techflow/secret-escrow` | `root:root 0700` | 선택적 암호화 Secret Escrow |
| `/var/log/ablestack-techflow/recovery-drills` | `root:ablecloud 0750` | 값이 없는 복구 증적 JSON |

상태 Archive에는 `.env`, `/etc/ablestack-techflow/secrets`와 `secret-audit.jsonl`을 포함하지 않는다.

## 3. 서버 배포

저장소의 다음 자산을 승인된 커밋에서 `/opt/ablestack-techflow/activepieces`의 동일 상대 경로로 복사한다.

```text
scripts/backup_manifest.py
scripts/backup-state.sh
scripts/restore-state-drill.sh
scripts/test-backup-recovery.sh
scripts/install-backup-timer.sh
scripts/verify-backup.sh
scripts/backup-secret-store.sh
scripts/restore-secret-store-drill.sh
scripts/test-secret-escrow.sh
systemd/techflow-state-backup.service
systemd/techflow-state-backup.timer
```

실행 권한과 문법을 확인한 뒤 Timer를 설치한다.

```bash
cd /opt/ablestack-techflow/activepieces
chmod 0755 scripts/backup*.sh scripts/restore*.sh scripts/test-*-recovery.sh \
  scripts/test-secret-escrow.sh scripts/install-backup-timer.sh \
  scripts/verify-backup.sh scripts/backup_manifest.py
bash -n scripts/backup-state.sh scripts/restore-state-drill.sh \
  scripts/test-backup-recovery.sh scripts/install-backup-timer.sh
python3 -m py_compile scripts/backup_manifest.py
sudo ./scripts/install-backup-timer.sh
```

정상 기준은 `techflow-state-backup.timer`가 `enabled`와 `active`이고 다음 실행 시각이 표시되는 것이다.

## 4. 수동 백업

```bash
cd /opt/ablestack-techflow/activepieces
sudo ./scripts/backup-state.sh --label manual --retention-days 7
sudo ./scripts/verify-backup.sh
```

Archive에는 다음 네 파일만 포함된다.

```text
manifest.json
checksums.sha256
postgres.dump
redis.rdb
```

`backup=created`, `checksums=valid`, `secrets=excluded`가 성공 기준이다. Archive 경로를 Issue나 외부 로그에 기록할 때도 파일 내용은 첨부하지 않는다.

## 5. 정기 백업

정기 백업은 매일 `02:30 UTC`에 실행하며 최대 10분 분산 지연을 적용한다.

```bash
systemctl list-timers techflow-state-backup.timer
sudo systemctl start techflow-state-backup.service
systemctl show techflow-state-backup.service -p Result -p ExecMainStatus
```

정상 기준은 `Result=success`, `ExecMainStatus=0`이다. Timer 실행 실패와 용량 경보는 Issue #17의 공통 로그·메트릭 체계에 연결한다.

## 6. 전체 복구 훈련

테스트 서버에서 운영 중단 없이 Backup 생성과 복구를 한 번에 검증한다.

```bash
cd /opt/ablestack-techflow/activepieces
sudo ./scripts/test-backup-recovery.sh
```

스크립트는 다음 순서로 동작한다.

1. PostgreSQL과 Redis에 비밀값이 아닌 동일 Probe ID를 기록한다.
2. 30일 보존 Label로 상태 Archive를 생성한다.
3. 운영 Probe를 제거한다.
4. 내부 전용 Docker Network와 두 개의 임시 Volume을 만든다.
5. PostgreSQL Dump와 Redis RDB를 각각 새 컨테이너에 복원한다.
6. Table 수, RDB 무결성, 양쪽 Probe와 공개 포트 0개를 확인한다.
7. 운영 Container ID와 전체 Health를 재확인한다.
8. 임시 Container·Network·Volume·평문을 제거하고 값이 없는 JSON 증적을 남긴다.

정상 출력:

```text
restore=passed isolated=true published_ports=0 ... cleanup=scheduled
recovery_drill=passed ... production_containers=unchanged production_health=pass
```

## 7. 특정 Archive 복구 검증

```bash
sudo ./scripts/restore-state-drill.sh \
  --archive /var/backups/ablestack-techflow/state/techflow-state-YYYYMMDDTHHMMSSZ-manual.tar.gz \
  --evidence-output /var/log/ablestack-techflow/recovery-drills/manual.json
```

이 명령은 운영 Compose 프로젝트를 정지하거나 Volume을 교체하지 않는다. 실패 원인 분석이 꼭 필요한 경우에만 `--keep-failed`를 추가한다. 분석 후 출력된 정확한 임시 자원만 제거한다.

## 8. 실제 장애 복구

실제 장애에서는 먼저 원본 Host와 Volume을 보존하고 새 서버 또는 격리된 복구 환경을 준비한다.

1. 승인된 Archive와 별도 Secret Escrow를 확보한다.
2. Archive Checksum과 암호화 Escrow 복호화를 격리 환경에서 검증한다.
3. 동일 Major의 PostgreSQL·Redis 이미지를 준비한다.
4. 이 Runbook의 격리 복구를 실행해 Table·Probe·Health를 확인한다.
5. TechFlow App·Worker가 원래 암호화 Key로 연결 데이터를 해독하는지 확인한다.
6. 제품 책임자와 운영자의 승인을 받은 후에만 DNS·Ingress 또는 서비스 연결을 복구 환경으로 전환한다.

자동 스크립트는 운영 Volume을 덮어쓰지 않는다. 실제 승격은 변경 승인과 별도의 전환 계획이 필요한 작업이다.

## 9. Secret Escrow

Passphrase 파일은 승인된 외부 Vault가 런타임에 제공하고 `root:root 0600`이어야 한다. Bundle과 같은 저장소에 두지 않는다.

```bash
sudo ./scripts/backup-secret-store.sh \
  --passphrase-file /run/credentials/techflow-escrow-passphrase \
  --output-dir /var/backups/ablestack-techflow/secret-escrow \
  --label manual

sudo ./scripts/restore-secret-store-drill.sh \
  --bundle /var/backups/ablestack-techflow/secret-escrow/techflow-secret-escrow-...gpg \
  --passphrase-file /run/credentials/techflow-escrow-passphrase
```

M0 절차 자체는 다음 명령으로 검증한다. 임시 Passphrase와 암호화 Bundle은 성공·실패와 관계없이 삭제되며 보호된 운영 Secret 파일은 변경하지 않는다.

```bash
sudo ./scripts/test-secret-escrow.sh
```

로컬 Secret Escrow만으로 Host 상실에 대비할 수 없다. 고객 Beta·GA에서는 암호화 Bundle과 Passphrase를 서로 다른 외부 장애 영역에 보관해야 한다.

## 10. 장애 분석

| 증상 | 확인 | 조치 |
|---|---|---|
| `pg_dump` 실패 | PostgreSQL Health·디스크 | Archive 부분 파일을 사용하지 않고 원인 해결 후 재실행 |
| Redis RDB 실패 | Redis 인증·Persistence 상태 | 운영 AOF를 직접 복사하지 말고 RDB 생성 원인을 해결 |
| Checksum 불일치 | Archive 권한·전송 경로 | Archive 폐기, 원본에서 새 백업 생성 |
| PostgreSQL 복원 실패 | 이미지 Major·Dump 로그 | 동일 Major 이미지에서 격리 재현 |
| Redis Key 수 차이 | Queue 처리 시각·Probe·RDB 검사 | Source 관측 수가 아닌 RDB 무결성과 Probe로 판정 |
| Timer 실패 | `systemctl status`, `journalctl` | 디스크·Docker·권한 복구 후 수동 1회 실행 |
| Secret 복호화 실패 | Passphrase·Bundle Checksum | 운영 Secret을 덮어쓰지 말고 Escrow 담당자에게 이관 |

## 11. 보안 점검

```bash
sudo ./scripts/verify-backup.sh
sudo find /var/backups/ablestack-techflow/state -maxdepth 1 -type f \
  -printf '%M %u:%g %f\n'
docker ps -aq --filter name=techflow-recovery
docker network ls -q --filter name=techflow-recovery
docker volume ls -q --filter name=techflow-recovery
```

백업 파일을 공개 Issue, 채팅, 일반 Artifact와 소스 저장소에 첨부하지 않는다. 복구 증적에는 시간·상태·개수·소요시간만 기록하고 데이터 값, 인증정보, Probe 원문과 내부 로그를 포함하지 않는다.
