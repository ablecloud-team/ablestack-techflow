# Activepieces Docker Compose 자산

ABLESTACK TechFlow 사내 실증 서버에 Activepieces Community Edition을 재현 가능하게 배포하기 위한 구성입니다.

## 구성

- Activepieces `0.86.3` App 1개
- Activepieces `0.86.3` Worker 1개, `AP_WORKER_CONCURRENCY=1`
- PostgreSQL `pgvector/pgvector:0.8.0-pg14`
- Redis `7.0.7`, AOF와 인증 사용
- PostgreSQL, Redis, Activepieces Cache 영속 볼륨
- HMAC·Timestamp·Redis 중복 방지 기능을 갖춘 Event Gateway
- UI와 Webhook 경로를 분리하는 Caddy Ingress
- 6개 서비스 헬스체크와 Worker Polling 확인
- PostgreSQL Custom Dump·Redis RDB 정기 백업과 격리 복구
- 별도 암호화 Secret Escrow와 복구 절차
- 사설 주소 `172.16.0.231:8080` 바인딩, 외부 HTTPS Proxy

실제 설치와 운영 절차는 [Activepieces Compose 배포 Runbook](../../../docs/runbooks/activepieces-compose-deployment.md), [HTTPS·Webhook Ingress 운영 Runbook](../../../docs/runbooks/https-webhook-ingress.md)과 [상태 백업·복구 Runbook](../../../docs/runbooks/state-backup-recovery.md)을 따른다.

최초 `.env`는 `scripts/init-env.sh`로 서버에서 생성한 뒤 `secretctl.sh bootstrap`으로 보호된 저장소에 이동한다. 저장소에는 실제 값을 커밋하지 않는다.

## 기본 실행

```bash
sudo bash scripts/install-docker-ubuntu.sh
./scripts/init-env.sh
./scripts/configure-ingress.sh https://techflow.ablecloud.io
sudo ./scripts/secretctl.sh bootstrap
./scripts/deploy.sh
./scripts/verify-persistence.sh
./scripts/verify-ingress.sh
./scripts/verify-secrets.sh
sudo ./scripts/install-backup-timer.sh
sudo ./scripts/test-backup-recovery.sh
sudo ./scripts/test-secret-escrow.sh
```

배포 후 운영자는 외부 HTTPS UI 또는 사설망 관리 경로에서 초기 플랫폼 관리자를 생성한다. 관리자 이메일과 비밀번호는 이 자산이나 GitHub Issue에 기록하지 않는다.

Secret 교체·폐기와 사고 대응은 [Secret 수명주기 Runbook](../../../docs/runbooks/secret-lifecycle.md)을 따른다. 상세한 사전 점검, 재부팅 복구, 업그레이드, 장애 분석과 안전한 제거 절차는 Runbook을 단일 운영 기준으로 사용한다.
