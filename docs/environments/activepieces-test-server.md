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

외부 포트 포워딩은 SSH `10023`만 확인했다. Activepieces HTTP 포트는 사설 주소 `172.16.0.231:8080`에만 바인딩했으며 PostgreSQL과 Redis 포트는 호스트에 공개하지 않는다.

## Activepieces 배포 상태

2026-07-30 다음 Compose 구성을 `/opt/ablestack-techflow/activepieces`에 배포했다.

| 서비스 | 이미지 | 상태 |
|---|---|---|
| App | `ghcr.io/activepieces/activepieces:0.86.3` | `healthy` |
| Worker | `ghcr.io/activepieces/activepieces:0.86.3` | `healthy`, Polling 준비 |
| PostgreSQL | `pgvector/pgvector:0.8.0-pg14` | `healthy` |
| Redis | `redis:7.0.7` | `healthy`, AOF·인증 사용 |

배포 시 확인한 이미지 Digest는 다음과 같다. 버전·Digest 갱신 정책과 정식 호환성 기준은 Issue #18에서 관리한다.

| 이미지 | Digest |
|---|---|
| Activepieces `0.86.3` | `sha256:208517c4f0d798a477a0c594bf432dd0f4918433f4b6f5b5f188a6e10e638c6c` |
| PostgreSQL | `sha256:c55d7e7deac05dde62139e0ded4fcf4f58363656cbc382dbea82fbed995aa767` |
| Redis | `sha256:bb474c35022ca2c5618f4c49ca759bd2c0eea1daf5d934c560bd30092b97b498` |

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

재부팅 검증 시 서버 Boot Time은 `2026-07-30 08:05:23 UTC`였으며, 복구 후 App은 약 807 MiB, Worker는 약 200 MiB, PostgreSQL은 약 176 MiB, Redis는 약 34 MiB를 사용했다. 이 수치는 단일 시점 관측값이며 용량 계획 기준은 아니다.

## 운영 자산

- [Activepieces Compose 배포 자산](../../deploy/compose/activepieces/README.md)
- [Activepieces Compose 배포 Runbook](../runbooks/activepieces-compose-deployment.md)

실제 비밀값은 서버의 `/opt/ablestack-techflow/activepieces/.env`에 권한 `0600`으로 생성했다. 저장소와 문서에는 값이 없는 `.env.example`만 포함한다.

다음 정보는 저장소에 커밋하지 않고 배포 환경의 비밀값으로 관리한다.

- Activepieces 암호화 키 및 JWT 시크릿
- 데이터베이스 및 Redis 인증정보
- GitHub Webhook 시크릿과 접근 토큰
- AI 서비스 API 키
- 사내 메신저 및 커뮤니티 연동 자격 증명

정식 비밀정보 저장·교체·폐기 방식은 Issue #15에서 확정한다. 현재 서버는 Issue #14의 HTTPS·Webhook 경로가 구성되기 전까지 사설망 실증용으로만 사용한다.
