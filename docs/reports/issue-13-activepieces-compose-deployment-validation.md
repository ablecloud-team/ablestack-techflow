# Issue #13 Activepieces Compose 배포 검증 기록

## 1. 결과

2026-07-30 Ubuntu 24.04 테스트 서버에 Activepieces `0.86.3`, PostgreSQL, Redis와 전용 Worker를 Docker Compose로 배포했다. 네 서비스의 Health, Worker Polling, 데이터 영속성, 서버 재부팅 후 자동 복구와 사설망 UI 접근을 확인했다.

## 2. 자산화 범위

| 자산 | 역할 |
|---|---|
| `deploy/compose/activepieces/compose.yml` | App·Worker·PostgreSQL·Redis와 볼륨·네트워크·Health 정의 |
| `.env.example` | 비밀값 없는 설정 계약 |
| `scripts/install-docker-ubuntu.sh` | Ubuntu 24.04 Docker 설치 |
| `scripts/init-env.sh` | 서버 런타임 비밀값 생성 |
| `scripts/deploy.sh` | 구성 검사·Pull·기동·종합 Health |
| `scripts/healthcheck.sh` | 네 서비스 Health와 Worker Polling 준비 검사 |
| `scripts/status.sh` | 서비스·HTTP·Worker·자원 상태 확인 |
| `scripts/verify-persistence.sh` | PostgreSQL·Redis 재시작 영속성 검증 |
| `scripts/remove.sh` | 기본 데이터 보존 제거와 명시적 데이터 삭제 |
| 배포 Runbook | 초기 설치부터 운영·장애·제거 절차 |

## 3. 실제 배포 과정

1. 내부 `172.16.0.231:22`와 외부 `211.115.222.251:10023` 경로를 확인했다.
2. 두 경로가 동일한 호스트명과 SSH Host Key를 반환하는 것을 확인했다.
3. Docker 공식 Ubuntu 저장소에서 Engine `29.6.2`와 Compose `v5.3.1`을 설치했다.
4. 배포 자산을 `/opt/ablestack-techflow/activepieces`에 설치했다.
5. 서버에서 `.env`를 생성하고 권한을 `0600`으로 제한했다.
6. Compose 구성 검증 후 고정 태그 이미지를 Pull하고 기동했다.
7. App·Worker·PostgreSQL·Redis Health와 사설망 HTTP `200`을 확인했다.
8. PostgreSQL·Redis를 재시작해 영속성을 확인했다.
9. 서버를 재부팅하고 Docker·컨테이너·Worker Polling의 자동 복구를 확인했다.
10. 준비 완료 이후 오류·경고와 비밀값 로그 노출이 없음을 확인했다.
11. `.env`를 제외한 저장소 배포 자산과 서버 배포 파일의 SHA-256이 모두 일치하고 운영 스크립트 권한이 `0755`임을 확인했다.

## 4. 구성 결정

- 3.8 GiB 테스트 서버에 App 1개와 Worker 1개를 사용한다.
- Worker는 `AP_WORKER_CONCURRENCY=1`로 한 번에 하나의 Flow만 실행한다.
- `AP_EXECUTION_MODE=SANDBOX_CODE_ONLY`와 `AP_NETWORK_MODE=STRICT`를 사용한다.
- App는 `172.16.0.231:8080`에만 바인딩한다.
- PostgreSQL과 Redis는 호스트 포트를 공개하지 않는다.
- Redis는 인증과 AOF를 사용한다.
- 이미지에는 `latest` 대신 명시적 버전을 사용한다.
- 이미지 Digest와 업그레이드 정책은 Issue #18에서 확정한다.

## 5. 검증 증거

| ID | 검증 | 결과 |
|---|---|---|
| V1 | 내부·외부 SSH와 동일 Host Key | 통과 |
| V2 | Docker·Compose 설치와 자동 시작 | 통과 |
| V3 | Compose 구성 해석 | 통과 |
| V4 | 네 서비스 Health | 통과 |
| V5 | HTTP Health·UI | 통과 |
| V6 | Worker API 연결과 Polling | 통과 |
| V7 | PostgreSQL·Redis 영속성 | 통과 |
| V8 | 서버 재부팅 자동 복구 | 통과 |
| V9 | 준비 완료 후 오류·경고 | 0건 |
| V10 | 런타임 비밀값 로그 노출 | 0건 |

## 6. 관찰 사항

서버 재부팅 직후 Worker는 App의 Socket.IO 준비가 끝날 때까지 연결을 재시도했다. 약 2분 후 연결되어 `concurrency=1` Polling을 시작했으며 이후 오류 이벤트는 없었다. Health 스크립트는 컨테이너 Health뿐 아니라 `Polling worker started` 로그까지 확인하도록 보강했다.

복구 후 단일 시점 메모리 사용량은 App 약 807 MiB, Worker 약 200 MiB, PostgreSQL 약 176 MiB, Redis 약 34 MiB였다. 장기 부하와 동시 실행 용량은 Issue #17과 #23의 관측·KPI 범위에서 검증한다.

## 7. 후속 작업

운영자는 사설망 UI에서 초기 플랫폼 관리자 계정을 생성한다. 관리자 이메일과 비밀번호는 저장소, Issue, 배포 스크립트와 보고 자료에 기록하지 않는다. 이 운영자 단계는 서버 배포와 Health 검증 완료 판정과 분리한다.

1. Issue #14: 외부 HTTPS·Webhook 경로와 서명 검증
2. Issue #15: Secret Broker, 교체와 폐기 정책
3. Issue #16: PostgreSQL·Redis 백업과 복구 훈련
4. Issue #17: 로그·메트릭·상태 점검과 경보
5. Issue #18: Activepieces 버전·이미지 Digest·업그레이드 정책
6. Issue #19: GitHub PR Merge Webhook 실증

## 8. 보안

SSH 비밀번호, 생성된 `.env`, API Key, JWT Secret, 암호화 키, PostgreSQL·Redis 비밀번호는 이 기록에 포함하지 않았다. 런타임 비밀값은 서버 로컬 파일에만 존재하며 정식 관리 방식은 Issue #15에서 보강한다.

## 9. 근거

- [GitHub Issue #13](https://github.com/ablecloud-team/ablestack-techflow/issues/13)
- [Activepieces Compose 배포 Runbook](../runbooks/activepieces-compose-deployment.md)
- [Activepieces 테스트 서버](../environments/activepieces-test-server.md)
- [Activepieces Docker Compose](https://www.activepieces.com/docs/install/options/docker-compose)
- [Activepieces Worker](https://www.activepieces.com/docs/install/architecture/workers)
- [Docker Engine Ubuntu 설치](https://docs.docker.com/engine/install/ubuntu/)
