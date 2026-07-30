# Activepieces Docker Compose 자산

ABLESTACK TechFlow 사내 실증 서버에 Activepieces Community Edition을 재현 가능하게 배포하기 위한 구성입니다.

## 구성

- Activepieces `0.86.3` App 1개
- Activepieces `0.86.3` Worker 1개, `AP_WORKER_CONCURRENCY=1`
- PostgreSQL `pgvector/pgvector:0.8.0-pg14`
- Redis `7.0.7`, AOF와 인증 사용
- PostgreSQL, Redis, Activepieces Cache 영속 볼륨
- App, Worker, PostgreSQL, Redis 헬스체크
- 사설 주소 `172.16.0.231:8080` 바인딩

실제 설치와 운영 절차는 [Activepieces Compose 배포 Runbook](../../../docs/runbooks/activepieces-compose-deployment.md)을 따른다.

`.env`는 `scripts/init-env.sh`로 서버에서 생성하고 저장소에 커밋하지 않는다.

## 기본 실행

```bash
sudo bash scripts/install-docker-ubuntu.sh
./scripts/init-env.sh
./scripts/deploy.sh
./scripts/verify-persistence.sh
```

배포 후 운영자가 사설망 UI에서 초기 플랫폼 관리자 계정을 생성한다. 관리자 이메일과 비밀번호는 이 자산이나 GitHub Issue에 기록하지 않는다.

상세한 사전 점검, 재부팅 복구, 업그레이드, 장애 분석과 안전한 제거 절차는 Runbook을 단일 운영 기준으로 사용한다.
