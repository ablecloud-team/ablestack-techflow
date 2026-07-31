# Activepieces Docker Compose 배포 Runbook

## 1. 목적

이 문서는 초기화된 Ubuntu 24.04 서버에 ABLESTACK TechFlow의 Activepieces 실증 환경을 배포하고 상태를 확인하는 표준 절차다. 실제 배포 자산은 [`deploy/compose/activepieces`](../../deploy/compose/activepieces/README.md)에 있다.

## 2. 적용 범위

| 항목 | 값 |
|---|---|
| 대상 운영체제 | Ubuntu 24.04 LTS `noble` |
| 배포 경로 | `/opt/ablestack-techflow/activepieces` |
| Activepieces | `ghcr.io/activepieces/activepieces:0.86.3` |
| PostgreSQL | `pgvector/pgvector:0.8.0-pg14` |
| Redis | `redis:7.0.7` |
| 내부 접속 URL | `http://172.16.0.231:8080` |
| 외부 접속 URL | `https://techflow.ablecloud.io` |
| 외부 HTTPS·Webhook | Issue #14 구성·검증 완료 |

현재 구성은 사내 실증용 단일 서버 배포다. Activepieces는 시각적 Flow 실행 계층이며 제품 정책, 승인, 감사와 ABLESTACK 자원 상태의 원장이 아니다.

## 3. 사전 확인

```bash
hostname
cat /etc/os-release
nproc
free -h
df -h /
timedatectl status
ss -lnt
```

다음 조건을 확인한다.

- Ubuntu 24.04 LTS
- 4 vCPU, 3.8 GiB RAM과 Swap
- 루트 파일시스템 여유 20 GiB 이상
- NTP 동기화
- 사설 주소 TCP `8080` 포트 미사용
- Docker Hub, GHCR과 Ubuntu 저장소로 HTTPS 통신 가능

## 4. 배포 자산 설치

저장소를 임시 작업 위치에 받은 뒤 배포 자산만 운영 경로로 복사한다.

```bash
sudo install -d -o ablecloud -g ablecloud /opt/ablestack-techflow
git clone https://github.com/ablecloud-team/ablestack-techflow.git /tmp/ablestack-techflow
sudo cp -a /tmp/ablestack-techflow/deploy/compose/activepieces /opt/ablestack-techflow/
sudo chown -R ablecloud:ablecloud /opt/ablestack-techflow/activepieces
cd /opt/ablestack-techflow/activepieces
```

개발 브랜치를 검증할 때는 승인된 커밋을 별도 임시 경로에서 받아 동일한 배포 디렉터리 구조로 복사한다. 운영 디렉터리를 Git worktree로 사용하지 않는다.

## 5. Docker 설치

```bash
cd /opt/ablestack-techflow/activepieces
sudo bash scripts/install-docker-ubuntu.sh
```

설치 후 다시 로그인하거나 현재 셸에서 다음을 실행한다.

```bash
newgrp docker
docker --version
docker compose version
systemctl is-active docker
```

설치 스크립트는 Docker 공식 Ubuntu 저장소를 사용하고 Docker Engine, containerd, Buildx와 Compose Plugin을 설치한다.

## 6. 런타임 비밀값 생성

```bash
cd /opt/ablestack-techflow/activepieces
./scripts/init-env.sh
stat -c '%a %U:%G %n' .env
```

정상 결과는 `.env` 권한 `600`이다. 스크립트는 다음 값을 서버에서 무작위로 생성하며 값을 출력하지 않는다.

- Activepieces API Key
- Activepieces Encryption Key
- JWT Secret
- PostgreSQL 비밀번호
- Redis 비밀번호
- TechFlow Webhook HMAC Secret

`.env`를 저장소, Issue, 채팅, 백업 로그 또는 보고서에 복사하지 않는다. `--force`는 의도적인 비밀값 교체와 영향 검토가 끝난 경우에만 사용한다.

## 7. 구성 검증과 배포

```bash
cd /opt/ablestack-techflow/activepieces
./scripts/configure-ingress.sh https://techflow.ablecloud.io
docker compose --env-file .env config --quiet
./scripts/deploy.sh
```

배포 스크립트는 다음 순서로 동작한다.

1. `.env` 존재 여부와 권한 확인
2. Compose 문법과 필수 변수 확인
3. 고정 태그 이미지 Pull
4. PostgreSQL·Redis 기동과 헬스체크
5. Activepieces App과 Worker 기동
6. Event Gateway와 Caddy Ingress 기동
7. 6개 서비스, 내부 HTTP와 Worker Polling 종합 확인

## 8. 상태 확인

```bash
cd /opt/ablestack-techflow/activepieces
./scripts/healthcheck.sh
./scripts/status.sh
```

개별 확인은 다음과 같다.

```bash
curl -fsS http://172.16.0.231:8080/api/v1/health
curl -fsS https://techflow.ablecloud.io/api/v1/health
docker compose --env-file .env ps
docker compose --env-file .env logs --tail 100 app worker event-gateway ingress
```

정상 기준은 6개 서비스가 `running/healthy`이고 내부·외부 Health와 Worker Polling이 성공하는 것이다. HTTPS·Webhook 세부 검증은 [전용 Runbook](https-webhook-ingress.md)을 따른다. 로그를 공유할 때는 연결정보, 사용자 입력과 토큰을 먼저 제거한다.

## 9. 초기 플랫폼 관리자 생성

배포와 Health 검증이 완료되면 운영자가 `https://techflow.ablecloud.io`에 접속해 초기 플랫폼 관리자 계정을 생성한다. 장애 분석과 제한된 관리 작업에는 사설망 URL을 사용할 수 있다.

- 관리자 이메일과 비밀번호는 운영자가 UI에서 직접 입력한다.
- 관리자 자격 증명은 저장소, GitHub Issue, 배포 스크립트, 채팅과 보고서에 기록하지 않는다.
- 계정 생성 결과와 접근 권한은 운영자가 별도 보안 절차에 따라 확인한다.
- 초기 관리자 생성은 App, Worker, PostgreSQL과 Redis의 배포 및 Health 판정과 분리한다.

외부 접속은 HTTPS만 사용하고 HTTP URL을 사용자에게 배포하지 않는다.

## 10. 영속성 검증

```bash
cd /opt/ablestack-techflow/activepieces
./scripts/verify-persistence.sh
```

이 스크립트는 PostgreSQL의 테이블 상태와 Redis의 임시 Probe를 기록한 후 PostgreSQL·Redis를 재시작한다. 재시작 후 동일 상태를 확인하고 Redis Probe를 삭제한다. 영속 볼륨 자체를 삭제하지 않는다.

## 11. 재시작과 서버 재부팅

컨테이너만 재시작한다.

```bash
docker compose --env-file .env restart
./scripts/healthcheck.sh --wait 300
```

서버 재부팅 검증은 다음 순서로 수행한다.

```bash
sudo reboot
```

SSH가 복구된 후 다음을 확인한다.

```bash
systemctl is-active docker
cd /opt/ablestack-techflow/activepieces
./scripts/healthcheck.sh --wait 300
./scripts/status.sh
```

모든 서비스의 `restart: unless-stopped` 정책 때문에 Docker 서비스가 시작되면 자동 복구되어야 한다.

## 12. 변경과 업그레이드

구성 변경 전 `.env`와 영속 데이터의 복구 가능성을 확인한다. 이미지 버전 변경은 Issue #18의 버전·Digest 정책과 회귀 검증을 거친다.

```bash
docker compose --env-file .env config --quiet
docker compose --env-file .env pull
docker compose --env-file .env up -d --remove-orphans
./scripts/healthcheck.sh --wait 300
```

`latest` 태그를 사용하지 않는다. Activepieces 실행 성공을 TechFlow 또는 ABLESTACK 자원 작업의 성공으로 해석하지 않는다.

## 13. 중지와 제거

데이터를 보존하면서 중지·제거한다.

```bash
./scripts/remove.sh
```

영속 볼륨 삭제는 복구 불가능한 작업이다. 백업과 대상 확인 후에만 다음처럼 명시적으로 수행한다.

```bash
CONFIRM_TECHFLOW_DATA_PURGE=DELETE ./scripts/remove.sh --purge-data
```

운영 디렉터리의 `.env`는 별도로 남는다. 제거 또는 서버 폐기 시 승인된 비밀정보 폐기 절차를 적용한다.

## 14. 장애 분석

| 증상 | 확인 | 조치 |
|---|---|---|
| App가 `unhealthy` | `docker compose logs app` | PostgreSQL·Redis, 환경변수와 메모리 확인 |
| Worker가 `unhealthy` | `docker compose logs worker` | App Health, Redis 연결과 Worker 토큰 생성 확인 |
| PostgreSQL 실패 | `docker compose logs postgres` | 볼륨 권한, 디스크, 비밀번호 일치 확인 |
| Redis 실패 | `docker compose logs redis` | AOF, 디스크와 비밀번호 일치 확인 |
| UI 접근 실패 | `ss -lnt`, `curl` | 사설 주소 바인딩과 방화벽 확인 |
| 재부팅 후 미복구 | `systemctl status docker` | Docker 자동 시작과 컨테이너 Restart 정책 확인 |

Blind Retry나 데이터 볼륨 삭제로 장애를 우회하지 않는다. 원인을 확인하고 상태가 불명확하면 로그와 볼륨을 보존한다.

## 15. 보안 영향

- Ingress 포트는 사설 주소에만 바인딩하고 외부는 TLS Proxy를 경유한다.
- PostgreSQL과 Redis 포트를 호스트에 공개하지 않는다.
- Redis 인증과 PostgreSQL 인증을 사용한다.
- `AP_NETWORK_MODE=STRICT`와 `AP_EXECUTION_MODE=SANDBOX_CODE_ONLY`를 사용한다.
- Worker 동시성은 `1`로 제한한다.
- Compose 컨테이너에 `no-new-privileges`를 적용한다.
- 외부 HTTPS, Webhook 서명과 프록시는 Issue #14에서 검증되었다.
- 정식 Secret Broker와 교체 정책은 Issue #15 범위다.
- PostgreSQL·Redis 백업과 복구 훈련은 Issue #16 범위다.
- 로그·메트릭·경보는 Issue #17 범위다.

## 16. 근거

- [Activepieces Docker Compose](https://www.activepieces.com/docs/install/options/docker-compose)
- [Activepieces 아키텍처](https://www.activepieces.com/docs/install/architecture/overview)
- [Activepieces Worker](https://www.activepieces.com/docs/install/architecture/workers)
- [Activepieces 환경변수](https://www.activepieces.com/docs/install/reference/environment-variables)
- [Docker Engine Ubuntu 설치](https://docs.docker.com/engine/install/ubuntu/)
- [GitHub Issue #13](https://github.com/ablecloud-team/ablestack-techflow/issues/13)
