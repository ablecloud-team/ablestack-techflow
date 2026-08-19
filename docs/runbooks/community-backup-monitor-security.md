# Community 백업·모니터링·보안 운영 Runbook

## 목적과 운영 위치

Flarum Community의 DB·애플리케이션·업로드를 복구 가능하게 보관하고, 서비스·용량·백업·AI 연동 이상을 Chat으로 알린다.

| 구분 | 위치 |
|---|---|
| 운영 App | `/var/www/html` |
| 운영 암호화 백업 | `/var/backups/techflow-flarum/managed` |
| 상태·Metric | `/var/lib/techflow-community-ops` |
| 운영 로그 | `/var/log/techflow-community-ops` |
| 설정 | `/etc/techflow-community-ops/ops.env` |
| Chat Secret | `/etc/techflow-community-ops/alert.env` |
| WSL 복구 Vault | `/srv/techflow-community-recovery` |

Secret 값은 Repository, Issue, PR, 보고서와 명령 출력에 기록하지 않는다.

## 설치와 갱신

```bash
cd deploy/flarum/operations
sudo ./community-install.sh install
sudoedit /etc/techflow-community-ops/ops.env
sudo gpg --homedir /var/lib/techflow-community-ops/gnupg --import recovery-public.asc
sudo ./community-install.sh apply-security
```

운영 `ops.env`의 수신자는 복구 Vault 공개키 Fingerprint여야 한다. Chat URL은 `alert.env`에 `TECHFLOW_CHAT_WEBHOOK_URL`로 저장하고 권한을 0600으로 제한한다. 개인키와 복호화 암호는 운영 서버에 복사하지 않는다.

## 일상 점검

```bash
systemctl is-active techflow-community-backup.timer techflow-community-monitor.timer
systemctl list-timers techflow-community-backup.timer techflow-community-monitor.timer
sudo jq . /var/lib/techflow-community-ops/status.json
sudo sed -n '1,120p' /var/lib/techflow-community-ops/metrics.prom
sudo journalctl -u techflow-community-backup.service -u techflow-community-monitor.service --since today --no-pager
```

정상 기준은 서비스 3/3 Active, HTTP 200/200/200, Backup Integrity true, Mail Driver smtp, Active Alert 0이다. Production의 Public URL은 NAT Hairpin을 사용하지 않고 Local Host+공개 Host Header 경로로 점검하며 실제 외부 HTTPS는 WSL 또는 외부 Probe에서 별도로 확인한다.

## 백업과 검증

```bash
sudo systemctl start techflow-community-backup.service
sudo /usr/local/libexec/techflow-community-ops/community-verify-backup.sh \
  /var/backups/techflow-flarum/managed/latest
```

백업 중 PHP-FPM이 잠시 정지되지만 Trap이 실패 시에도 다시 시작한다. Monitor는 Backup Lock을 확인해 이 구간의 HTTP 실패를 장애로 오인하지 않는다. `.partial-*`은 실패 시 제거되며 완성된 Directory만 `latest`가 가리킨다.

## 외부 복사와 WSL 복원

운영 서버에서 암호화 파일만 Export한다.

```bash
sudo /usr/local/libexec/techflow-community-ops/community-offsite-export.sh ablecloud
```

WSL 복구 Vault에서 Pull한 뒤 별도 경로·별도 DB로 복원한다.

```bash
scp ablecloud@172.16.0.234:~/techflow-community-offsite/community-*.tar \
  /srv/techflow-community-recovery/offsite/

sudo /usr/local/libexec/techflow-community-ops/community-restore.sh \
  /srv/techflow-community-recovery/offsite/community-YYYYMMDDTHHMMSSZ \
  /srv/techflow-flarum-restore/app \
  flarum_restore
```

WSL `ops.env`에 GPG Homedir, Passphrase File과 `TECHFLOW_RESTORE_SOCKET_USER=www-data`를 지정한다. 복원 스크립트는 운영 App Root를 기본 거부한다. 복원 후 Flarum CLI, 핵심 Table 건수와 격리 HTTP를 확인한다.

## 경보 대응

| 경보 | 확인 | 우선 조치 |
|---|---|---|
| `service:*` | 해당 systemd Unit | 대상 서비스만 재시작 후 재수집 |
| `http:community-*` | Local Host Header, Nginx/PHP 로그 | 전체 재배포 없이 실패 계층만 복구 |
| `http:ai-orchestration` | TechFlow Health와 Community Poller | Flarum 서비스와 분리해 TechFlow 측 진단 |
| `backup:integrity` | Timer, 최신 Manifest와 Journal | 평문 복구 시도 금지, 새 백업 생성 |
| `capacity:filesystem` | `df -h`, `df -i`, 업로드 보존 | 만료·고아 파일 정리 후 업로드 제한 검토 |
| `security:mail-driver` | Flarum Mail Driver | 즉시 smtp로 복귀, Sendmail 사용 금지 |

같은 Fingerprint는 1시간 동안 다시 보내지 않는다. 상태가 정상으로 바뀌면 복구 알림을 한 번 보낸다.

## 보안 점검

```bash
sudo stat -c '%a %U:%G %n' \
  /var/www/html/config.php \
  /etc/techflow-community-ops/ops.env \
  /etc/techflow-community-ops/alert.env
curl -fsSI https://community.ablecloud.io/
sudo nginx -t
sudo logrotate -d /etc/logrotate.d/techflow-community-ops
```

`config.php` 0640, 두 운영 설정 0600, HTTP 200과 5개 보안 헤더가 정상이어야 한다. 운영 App의 World-writable 일반 파일은 0건이어야 한다.

## 롤백

관측만 중지하려면 다음을 실행한다.

```bash
sudo systemctl disable --now techflow-community-monitor.timer
```

Nginx 정책을 되돌릴 때는 적용 시 출력된 정확한 Backup Directory를 확인하고 사이트 설정을 복원한다.

```bash
sudo cp -a /var/backups/techflow-flarum/security-YYYYMMDDTHHMMSSZ/flarum-site.conf \
  /etc/nginx/sites-available/flarum
sudo rm -f /etc/nginx/conf.d/techflow-community-security-zone.conf
sudo rm -f /etc/nginx/snippets/techflow-community-security-server.conf
sudo nginx -t && sudo systemctl reload nginx
```

백업 Timer와 Archive는 장애 분석·복구 자산이므로 별도 승인 없이 삭제하지 않는다. 운영 DB나 App Root에 자동 복원하지 않는다.
