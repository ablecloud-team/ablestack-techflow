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

```bash
ssh -p 10023 ablecloud@211.115.222.251
```

인증정보는 운영자가 접속 시점에 입력하거나 승인된 비밀 관리 수단으로 전달한다. 비밀번호, API 키, 토큰 및 개인키는 이 공개 저장소의 문서·스크립트·환경 파일에 저장하지 않는다.

## 확인된 시스템 사양

2026-07-23 SSH 접속을 통해 다음 상태를 확인했다.

| 항목 | 확인 결과 |
|---|---|
| 운영체제 | Ubuntu 24.04.4 LTS (Noble Numbat) |
| 커널 | `7.0.0-28-generic` (`x86_64`) |
| CPU | 4 vCPU |
| 메모리 | 3.8 GiB, 확인 당시 약 3.3 GiB 사용 가능 |
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
| Docker Engine | 미설치 |
| Docker Compose | 미설치 |
| Podman | 미설치 |
| Node.js / npm | 미설치 |
| Java | 미설치 |
| Activepieces | 미설치 |

확인 당시 외부에 제공되는 서비스는 SSH뿐이며, 서버 내부에서는 TCP `22` 포트가 수신 중이다. 외부 접속 포트 `10023`은 이 SSH 서비스로 전달된다.

## Activepieces 설치 준비 상태

서버 자원과 외부 통신은 기본적인 기능 검증 및 소규모 사내 자동화 실증에 사용할 수 있는 상태다. 다만 컨테이너 런타임이 없으므로 Activepieces 배포 전에 Docker Engine과 Docker Compose 플러그인 설치가 필요하다.

설치 단계에서는 다음 정보를 저장소에 커밋하지 않고 배포 환경의 비밀값으로 관리한다.

- Activepieces 암호화 키 및 JWT 시크릿
- 데이터베이스 및 Redis 인증정보
- GitHub Webhook 시크릿과 접근 토큰
- AI 서비스 API 키
- 사내 메신저 및 커뮤니티 연동 자격 증명
