# TechFlow 이미지 버전 업그레이드·롤백 Runbook

## 1. 목적

Activepieces 기반 TechFlow Compose 환경을 검토된 이미지로 재현 가능하게 배포하고, 장애 시 직전 이미지 조합으로 데이터 손실 없이 복귀한다.

## 2. 운영 원칙

- 평상시 배포는 `deploy-locked.sh`만 사용한다.
- 외부 이미지는 반드시 `Tag@sha256:Digest` 형식으로 고정한다.
- Event Gateway는 M0 테스트 서버에서 사전 빌드한 승인 이미지 ID를 사용한다.
- 배포와 롤백 중에는 이미지를 빌드하지 않는다.
- `.env`나 Secret 값을 잠금·증적·Issue에 복사하지 않는다.
- DB Schema 비호환이 의심되면 이미지 롤백 전에 상태 복구 필요성을 판단한다.

## 3. 현재 릴리스 확인

```bash
cd /opt/ablestack-techflow/activepieces
python3 scripts/release_lock.py validate \
  --lock image-lock.json \
  --compose compose.yml \
  --dockerfile event-gateway/Dockerfile
sudo python3 scripts/release_lock.py verify-running --lock image-lock.json
sudo /usr/local/libexec/techflow-observer status
```

정상 기준은 `services=6 digests=verified health=healthy`, `services_healthy=6/6`, Critical·Warning 0이다.

## 4. 새 릴리스 준비

1. 별도 작업 브랜치에서 공급자 릴리스 노트, 마이그레이션, 보안 공지를 검토한다.
2. `image-lock.json`의 `releaseId`, `createdAt`, 버전과 Digest를 갱신한다.
3. Compose 기본 이미지와 Gateway Dockerfile Base Digest를 같은 값으로 맞춘다.
4. 외부 이미지는 Registry가 반환한 플랫폼별 Digest를 독립적으로 확인한다.
5. Gateway는 새 버전용 Tag로 한 번 빌드하고 출력 Image ID를 잠금 파일에 기록한다.

Gateway 최초 빌드용 잠금에는 검토 중인 `expectedImageId`를 사용하고 다음 명령의 출력값을 승인 잠금에 반영한다. 최종 잠금 후 빌드 명령이 Image ID 불일치로 실패하는 것은 변경 감지 동작이다.

```bash
sudo ./scripts/build-gateway-release.sh image-lock.json
```

제품 배포에서는 Gateway를 승인 Registry에 게시하고 로컬 Image ID 대신 Registry Digest로 전환한다.

## 5. 사전 점검

```bash
cd /opt/ablestack-techflow/activepieces
python3 -m unittest -v scripts/test_release_lock.py
sudo ./scripts/verify-image-lock.sh image-lock.json
docker volume ls --filter name=techflow-activepieces
df -h / /var/lib/docker /var/backups/ablestack-techflow
```

데이터 마이그레이션이 포함된 경우 운영 책임자의 유지보수 창과 데이터 롤백 방식을 먼저 승인받는다.

## 6. 잠금 배포

```bash
cd /opt/ablestack-techflow/activepieces
sudo ./scripts/deploy-locked.sh image-lock.json
```

스크립트는 다음을 자동 수행한다.

1. 잠금과 소스 일치 검증
2. 직전 Runtime Lock 생성
3. PostgreSQL·Redis 상태 백업
4. 외부 이미지 Digest Pull과 Gateway Image ID 확인
5. `docker compose up -d --no-build`
6. 6개 Health·Digest·Observer 확인
7. 현재 Runtime Lock과 최근 10개 릴리스 이력 보관

배포 후 확인:

```bash
sudo ./scripts/verify-image-lock.sh image-lock.json
curl -fsS -o /dev/null -w '%{http_code}\n' https://techflow.ablecloud.io/
sudo /usr/local/libexec/techflow-observer status
```

## 7. 롤백

최근 직전 잠금 확인:

```bash
sudo jq '{releaseId, createdAt, services: (.services | keys)}' \
  /var/lib/ablestack-techflow/releases/runtime-lock.previous.json
```

로컬 이미지 존재 여부를 확인하고 롤백한다.

```bash
cd /opt/ablestack-techflow/activepieces
sudo ./scripts/rollback-release.sh \
  /var/lib/ablestack-techflow/releases/runtime-lock.previous.json
```

롤백은 Pull과 Build 없이 실행된다. 성공 후 6개 Health, 외부 HTTPS, Observer를 다시 확인한다.

### 데이터 호환성이 깨진 경우

이미지 롤백만으로 복구하지 않는다.

1. 외부 Ingress를 차단하고 변경을 동결한다.
2. 실패한 배포 직전 백업을 선택한다.
3. [상태 백업·복구 Runbook](state-backup-recovery.md)에 따라 격리 복구 검증을 먼저 수행한다.
4. 승인된 유지보수 창에서 PostgreSQL·Redis 상태를 복원한다.
5. 직전 Runtime Lock으로 이미지를 전환한다.
6. Health·업무 데이터·Webhook 재처리 정책을 확인한다.

## 8. 릴리스 드릴

테스트 서버에서만 다음 자동 드릴을 실행한다.

```bash
sudo ./scripts/test-image-release.sh image-lock.json issue-18-image-lock
```

드릴은 고정 배포, 같은 설정 반복 배포, 직전 이미지 롤백, 목표 릴리스 복귀와 Volume 보존을 확인한다. 실행 중 컨테이너가 재생성되므로 업무 Flow가 없는 검증 창에서 수행한다.

## 9. 증적과 보존

| 자산 | 경로 | 기준 |
|---|---|---|
| 승인 소스 잠금 | `image-lock.json` | Git 검토·승인 |
| 직전 Runtime Lock | `/var/lib/ablestack-techflow/releases/runtime-lock.previous.json` | `root:root 0640` |
| 현재 Runtime Lock | `/var/lib/ablestack-techflow/releases/runtime-lock.current.json` | `root:root 0640` |
| 릴리스 이력 | `/var/lib/ablestack-techflow/releases/history/` | 최근 10개 |
| 드릴 결과 | `/var/log/ablestack-techflow/release-drills/` | `root:root 0640` |
| 상태 백업 | `/var/backups/ablestack-techflow/state/` | ADR-0003 정책 |

## 10. 장애 판단

다음 중 하나면 배포를 실패로 판정하고 신규 잠금을 승인하지 않는다.

- 잠금 형식 또는 Compose·Dockerfile 일치 검증 실패
- Gateway 기대 Image ID 불일치
- 6개 중 하나라도 Unhealthy
- 반복 배포 Runtime Image ID 불일치
- 로컬 이미지 부재로 무빌드 롤백 불가
- Volume 이름 변경 또는 데이터 호환성 미확인
- 외부 HTTPS 실패, Observer Critical·Warning 발생
- 릴리스 자산 Secret Scan 유출 발견
