# TechFlow 관측성 운영 Runbook

## 1. 목적

Activepieces 기반 TechFlow 테스트 서버의 서비스, 엔드포인트, PostgreSQL, Redis, 백업과 안전한 로그 집계를 확인하고 장애 원인을 추적한다.

## 2. 설치와 갱신

```bash
cd /opt/ablestack-techflow/activepieces
docker compose --env-file .env config
sudo ./scripts/install-observability.sh
```

Docker logging driver 변경 시에는 컨테이너 재생성이 필요하다. 먼저 상태 백업을 만들고 재생성 후 Health를 확인한다.

```bash
sudo ./scripts/backup-state.sh --label pre-observability-change --retention-days 7
docker compose --env-file .env up -d --remove-orphans
./scripts/healthcheck.sh --wait 300
```

## 3. 일상 점검

```bash
systemctl is-enabled techflow-observer.timer
systemctl is-active techflow-observer.timer
sudo /usr/local/libexec/techflow-observer status
sudo systemctl start techflow-observer.service
sudo journalctl -u techflow-observer.service --since today --no-pager
```

정상 기준은 `critical=0`, `warning=0`, `services_healthy=6/6`이다. `observer.service`는 `Type=oneshot`이므로 수집이 끝난 뒤 `inactive (dead)`인 것이 정상이다. Timer의 `active` 여부와 최근 Service Result를 함께 본다.

## 4. 상태와 메트릭 조회

```bash
sudo jq . /var/lib/ablestack-techflow/observability/status.json
sudo sed -n '1,160p' /var/lib/ablestack-techflow/observability/metrics.prom
sudo jq . /var/lib/ablestack-techflow/observability/current-alerts.json
sudo tail -n 50 /var/log/ablestack-techflow/observability/alerts.jsonl
sudo journalctl -t techflow-alert --since today --no-pager
```

출력물을 외부 Ticket이나 공개 Issue에 붙여 넣지 않는다. 외부 공유 시에는 경보 키, 심각도, 컴포넌트, 시간과 조치 결과만 재작성하며 원문 로그·요청·식별자는 제외한다.

## 5. 경보 대응

### 서비스 또는 Endpoint Critical

```bash
cd /opt/ablestack-techflow/activepieces
docker compose --env-file .env ps
./scripts/healthcheck.sh --wait 30
sudo journalctl -u techflow-observer.service -n 50 --no-pager
```

문제가 있는 서비스만 `docker compose restart <service>`로 복구한다. 전체 Volume 삭제나 `down -v`는 복구 절차가 아니며 실행하지 않는다.

### PostgreSQL·Redis Critical

```bash
docker compose --env-file .env exec -T postgres \
  sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
docker compose --env-file .env exec -T redis \
  sh -c 'REDISCLI_AUTH="$AP_REDIS_PASSWORD" redis-cli ping'
```

명령 출력에 Secret을 포함하지 않는다. Persistence 실패나 손상이 의심되면 [상태 백업·복구 Runbook](state-backup-recovery.md)을 따른다.

### Backup Critical

```bash
systemctl status techflow-state-backup.timer --no-pager
systemctl show techflow-state-backup.service -p Result -p ExecMainStatus
sudo ./scripts/verify-backup.sh
```

### Flow 실패 Warning·Critical

Observer는 상태별 건수만 제공한다. Activepieces UI에서 해당 시간대의 실행을 운영 권한으로 조회하되 Flow 입력·출력이나 고객 데이터를 공개 Issue에 복사하지 않는다.

## 6. 장애 감지 훈련

다음 스크립트는 `event-gateway`만 잠시 중단해 Critical 감지와 복구 전이를 확인한다.

```bash
cd /opt/ablestack-techflow/activepieces
sudo ./scripts/test-observability.sh issue-17-gateway
```

성공 출력:

```text
drill=issue-17-gateway detection=passed root_cause=event-gateway recovery=passed
```

훈련 후 반드시 다음을 확인한다.

```bash
./scripts/healthcheck.sh --wait 180
sudo /usr/local/libexec/techflow-observer status
curl -fsS https://techflow.ablecloud.io/api/v1/health >/dev/null
```

## 7. 전체 검증

```bash
cd /opt/ablestack-techflow/activepieces
sudo ./scripts/verify-observability.sh
```

검증은 단위 테스트, 수집기 Strict 실행, 파일 권한, 핵심 메트릭, Timer, 전체 Health와 관측 자산 Secret Scan을 수행한다.

## 8. 변경과 롤백

Observer만 롤백하려면 Timer를 비활성화하고 Unit 및 설치 파일을 제거한다. 상태 파일은 운영 증적이므로 삭제 전 보존 정책과 담당자 승인을 확인한다.

```bash
sudo systemctl disable --now techflow-observer.timer
sudo rm /etc/systemd/system/techflow-observer.service
sudo rm /etc/systemd/system/techflow-observer.timer
sudo rm /etc/systemd/system/techflow-observer-notify@.service
sudo systemctl daemon-reload
```

Docker logging driver를 이전 값으로 되돌리면 다시 컨테이너 재생성이 필요하다. 데이터 Volume은 제거하지 않는다.
