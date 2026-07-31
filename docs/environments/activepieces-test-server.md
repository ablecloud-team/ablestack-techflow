# Activepieces 테스트 서버

ABLESTACK TechFlow의 Activepieces 설치·실행 검증과 사내 프로세스 자동화 실증에 사용하는 서버입니다.

## 접속 정보

| 항목 | 값 |
|---|---|
| 외부 SSH 주소 | `211.115.222.251` |
| 외부 SSH 포트 | `10023` |
| SSH 계정 | `ablecloud` |
| 내부 호스트명 | `u24-base` |
| 내부 주소 | `172.16.0.231/24` |
| 내부 SSH 포트 | `22` |

```bash
# 사설망에서 직접 접속
ssh -p 22 ablecloud@172.16.0.231

# 외부망에서 포트 포워딩을 통해 접속
ssh -p 10023 ablecloud@211.115.222.251
```

인증정보는 운영자가 접속 시점에 입력하거나 승인된 비밀 관리 수단으로 전달한다. 비밀번호, API 키, 토큰 및 개인키는 이 공개 저장소의 문서·스크립트·환경 파일에 저장하지 않는다.

## 확인된 시스템 사양

2026-07-30 Issue #13 배포 전·후 SSH 접속을 통해 다음 상태를 재확인했다.

| 접속 경로 | 확인 결과 |
|---|---|
| 사설망 직접 접속 | `172.16.0.231:22` SSH 로그인 성공 |
| 외부 포트 포워딩 접속 | `211.115.222.251:10023` SSH 로그인 성공 |

두 경로가 동일한 `ssh-ed25519` 호스트 키 `SHA256:uhqc0M7okWRf6I53PF6qqSIUc9j1KHD5ImQRlqvfm3o`와 호스트명 `u24-base`를 반환하는 것을 확인했다. SSH 서비스는 서버의 IPv4 및 IPv6 전체 인터페이스에서 TCP `22` 포트를 수신한다.

| 항목 | 확인 결과 |
|---|---|
| 운영체제 | Ubuntu 24.04.4 LTS (Noble Numbat) |
| 커널 | `7.0.0-28-generic` (`x86_64`) |
| CPU | 4 vCPU |
| 메모리 | 3.8 GiB, 배포 전 약 3.3 GiB 사용 가능 |
| Swap | 3.8 GiB |
| 루트 파일시스템 | ext4/LVM, 46 GiB 중 약 37 GiB 사용 가능 |
| 시스템 시간대 | UTC, NTP 동기화 활성 |
| 외부 통신 | DNS 확인 및 GitHub HTTPS 접속 정상 |
| 권한 | `ablecloud` 계정은 `sudo` 그룹 소속이며 sudo 실행 시 비밀번호 필요 |

## 소프트웨어 및 서비스 상태

| 구성요소 | 상태 |
|---|---|
| Git | 설치됨 (`2.43.0`) |
| curl / wget | 설치됨 |
| Python | 설치됨 (`3.12.3`) |
| Docker Engine | 설치됨 (`29.6.2`) |
| Docker Compose | 설치됨 (`v5.3.1`) |
| Podman | 미설치 |
| Node.js / npm | 미설치 |
| Java | 미설치 |
| Activepieces | 설치·실행 중 (`0.86.3`) |

Activepieces 서비스는 사설 주소 `172.16.0.231:8080`에만 바인딩한다. 외부 사용자는 Cloudflare와 공개 TLS Origin을 경유해 `https://techflow.ablecloud.io`로 접속하며, HTTP 요청은 `308`로 HTTPS에 전환된다. 공개 `8080`, PostgreSQL과 Redis 포트는 열지 않는다.

## Activepieces 배포 상태

2026-07-30 기본 Compose 구성을 배포했고 2026-07-31 Issue #14에서 HTTPS와 Webhook Ingress를 추가했다.

| 서비스 | 이미지 | 상태 |
|---|---|---|
| App | `ghcr.io/activepieces/activepieces:0.86.3` | `healthy` |
| Worker | `ghcr.io/activepieces/activepieces:0.86.3` | `healthy`, Polling 준비 |
| PostgreSQL | `pgvector/pgvector:0.8.0-pg14` | `healthy` |
| Redis | `redis:7.0.7` | `healthy`, AOF·인증 사용 |
| Event Gateway | 로컬 Python 3.12 Alpine 이미지 | `healthy`, HMAC·중복 검증 |
| Ingress | `caddy:2.8.4-alpine` | `healthy`, 경로 분기·보안 헤더 |

배포 시 확인한 이미지 Digest는 다음과 같다. 버전·Digest 갱신 정책과 정식 호환성 기준은 Issue #18에서 관리한다.

| 이미지 | Digest |
|---|---|
| Activepieces `0.86.3` | `sha256:208517c4f0d798a477a0c594bf432dd0f4918433f4b6f5b5f188a6e10e638c6c` |
| PostgreSQL | `sha256:c55d7e7deac05dde62139e0ded4fcf4f58363656cbc382dbea82fbed995aa767` |
| Redis | `sha256:bb474c35022ca2c5618f4c49ca759bd2c0eea1daf5d934c560bd30092b97b498` |
| Caddy `2.8.4-alpine` | `sha256:af32e97344dc5b105fb68042792e80399ff8a4f01b46c5c17a00f6169b262c17` |
| Event Gateway | `sha256:eb5bf8b2e069f3de91d55f718f14f54fd56f63fc5741ce50979143947d75a5df` |

## 배포 검증 결과

| 검증 | 결과 |
|---|---|
| Compose 구성 검증 | 통과 |
| App·Worker·PostgreSQL·Redis Health | 모두 통과 |
| 사설망 HTTP Health | `200`, `{"status":"Healthy"}` |
| Activepieces UI | HTTP `200`, 정적 애플리케이션 로드 |
| Worker 준비 | API Socket 연결 후 `concurrency=1` Polling 시작 |
| PostgreSQL 영속성 | 컨테이너 재시작 후 유지 |
| Redis 영속성 | AOF Probe 재시작 검증 통과 |
| 서버 재부팅 복구 | Docker와 네 컨테이너 자동 복구 |
| 재부팅 후 두 SSH 경로 | 모두 로그인 성공 |
| 준비 완료 후 오류 이벤트 | `0` |
| 런타임 비밀값 로그 노출 | `0` |
| 외부 HTTP→HTTPS | `308`, 경로·쿼리 보존 |
| 외부 HTTPS UI·Health | TLS 검증과 HTTP `200` |
| 유효 서명 Webhook | `202` |
| 중복·위조·오래된 요청 | `409`·`401`·`401` |
| Ingress 재시작·서버 재부팅 | 6개 서비스와 Webhook 재검증 통과 |
| PostgreSQL·Redis 상태 백업 | Manifest·SHA-256·Secret 제외 검증 통과 |
| 격리 복구 | 40초, PostgreSQL·Redis Probe 통과 |
| 복구 임시 자원 | Container·Network·Volume 모두 0개 |
| 정기 Backup Timer | 활성, 실제 1회 실행 `success` |

재부팅 검증 시 서버 Boot Time은 `2026-07-30 08:05:23 UTC`였으며, 복구 후 App은 약 807 MiB, Worker는 약 200 MiB, PostgreSQL은 약 176 MiB, Redis는 약 34 MiB를 사용했다. 이 수치는 단일 시점 관측값이며 용량 계획 기준은 아니다.

## 운영 자산

- [Activepieces Compose 배포 자산](../../deploy/compose/activepieces/README.md)
- [Activepieces Compose 배포 Runbook](../runbooks/activepieces-compose-deployment.md)
- [HTTPS·Webhook Ingress 운영 Runbook](../runbooks/https-webhook-ingress.md)

Issue #15에서 실제 비밀값을 `/etc/ablestack-techflow/secrets/activepieces.env`로 이동했다. 파일은 `root:ablecloud 0640`, 상위 디렉터리는 `0750`이며 배포 경로의 `.env`는 보호된 파일을 가리키는 심볼릭 링크다. 저장소와 문서에는 값이 없는 `.env.example`만 포함한다.

다음 정보는 저장소에 커밋하지 않고 배포 환경의 비밀값으로 관리한다.

- Activepieces 암호화 키 및 JWT 시크릿
- 데이터베이스 및 Redis 인증정보
- GitHub Webhook 시크릿과 접근 토큰
- AI 서비스 API 키
- 사내 메신저 및 커뮤니티 연동 자격 증명

Secret 변경 감사는 `/var/log/ablestack-techflow/secret-audit.jsonl`에 실제 값 없이 기록한다. Webhook Secret의 현재·직전 Grace Period와 폐기, 저장소·로그 노출 0건 및 서버 재부팅 복구를 Issue #15에서 검증했다. 상세 절차는 [Secret 수명주기 Runbook](../runbooks/secret-lifecycle.md)을 따른다.

Issue #14에서 생성한 `.env` 포함 구형 Archive는 Issue #16 복구 검증 후 안전 삭제했다. 값이 없는 Issue #15 사전 배포 Archive만 `root:root 0600`으로 보존한다. Issue #16의 상태 Archive는 `.env`와 Secret 저장소를 제외한다. 보호된 Secret 파일은 별도 OpenPGP AES-256 Escrow와 격리 복호화 절차를 검증했으며, 실제 고객 배포에서는 암호화 Bundle과 Passphrase를 서로 다른 승인된 외부 장애 영역에 보관해야 한다.

PostgreSQL·Redis Backup은 `/var/backups/ablestack-techflow/state`에 `root:ablecloud 0640`으로 저장된다. 매일 `02:30 UTC`에 실행하는 Timer와 운영 Volume을 사용하지 않는 격리 복구 절차는 [상태 백업·복구 Runbook](../runbooks/state-backup-recovery.md)을 따른다.
