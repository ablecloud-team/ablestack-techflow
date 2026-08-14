# Community 대용량 첨부 운영 Runbook

## 목적

Community 질문에 이미지, 일반 로그, ZIP, GZIP, TAR.GZ를 첨부했을 때 Flarum 수신부터 TechFlow AI 분석까지 일관된 경계로 처리한다. 실행 파일, 경로 이탈, 심볼릭 링크, 중첩 압축, 압축 폭탄, MIME 위장은 닫힌 상태로 거부한다.

```mermaid
flowchart LR
    U["사용자 - 파일당 최대 50 MiB"] --> N["Nginx - 요청 120 MiB, 300초"]
    N --> P["PHP-FPM - 요청 64 MiB, 300초"]
    P --> F["Flarum/FoF Upload - 파일 50 MiB"]
    F --> C["Community Poller - 50 MiB, 120초, 2회 재시도"]
    C --> G["AI Gateway - 원본 50 MiB"]
    G --> S["압축 안전검사 - 해제 100 MiB, 100개, 20배"]
    S --> A["AI 답변 - 24시간 보관 후 삭제"]
```

## 운영 경계

| 계층 | 기준 | 운영값 |
|---|---|---:|
| Nginx | 요청 본문 상한 | 120 MiB |
| Nginx | 본문/응답 대기 | 300초 |
| PHP-FPM | 파일/요청 | 64 MiB / 64 MiB |
| PHP-FPM | 실행/입력/메모리 | 300초 / 300초 / 256 MiB |
| FoF Upload | 파일당 상한 | 50 MiB (51,200 KiB) |
| Poller | 다운로드/시간/재시도 | 50 MiB / 120초 / 2회 |
| AI Gateway | 원본/압축 해제 | 50 MiB / 100 MiB |
| AI Gateway | 압축 항목/압축비 | 100개 / 20배 |
| Artifact | 보관/점검 | 24시간 / 15분 |
| 디스크 | 경고/위험 | 70% / 85% |

바깥 계층의 요청 한도는 안쪽의 파일 한도보다 크게 유지한다. 따라서 멀티파트 부가정보가 포함되어도 50 MiB 파일이 FoF Upload까지 도달한다.

## 허용 및 거부

허용 대상은 PNG/JPEG/WebP 등 이미지, UTF-8 일반 텍스트 로그, ZIP, GZIP, TAR.GZ/TGZ다. PDF는 Community 보관은 가능하지만 현재 TechFlow 로그 분석 대상은 아니다.

다음 조건은 분석에서 제외하고 사용자에게 재첨부 안내를 전달한다.

- 50 MiB 초과 파일
- Community 외부 주소
- ZIP/TAR 내부 경로 이탈, 절대 경로, 드라이브 경로
- 심볼릭 링크, 파이프, 장치 등 특수 파일
- 실행 파일 또는 중첩 압축
- 압축 해제 100 MiB, 항목 100개, 압축비 20배 초과
- 확장자와 실제 바이트가 다른 이미지 및 바이너리 로그

## 적용

Flarum 서버에서 다음 스크립트를 사용한다.

```bash
sudo /usr/local/sbin/techflow-flarum-upload-policy apply
sudo /usr/local/sbin/techflow-flarum-upload-policy verify
```

TechFlow는 `deploy/compose/ai-gateway/compose.yml`과 런타임 전용 `.env`에 동일한 값을 설정한 뒤 다음 서비스만 교체한다.

```bash
docker compose -f compose.yml -f compose.openai.override.yml config --quiet
docker compose -f compose.yml -f compose.openai.override.yml up -d --no-deps \
  gateway community-poller artifact-maintainer
```

GitHub→Chat 보호 서비스는 배포 대상이 아니다. 배포 후 보호 검사를 반드시 실행한다.

```bash
cd /opt/ablestack-techflow/activepieces
sudo python3 scripts/protected_service_guard.py \
  --lock protected-services.json --env-file .env \
  --compose compose.yml --ingress ingress/Caddyfile
```

## 확인

```bash
sudo /usr/local/sbin/techflow-flarum-upload-policy verify
docker inspect techflow-ai-gateway-gateway-1 --format '{{.State.Health.Status}}'
docker logs --tail 20 techflow-ai-gateway-community-poller-1
docker logs --tail 20 techflow-ai-gateway-artifact-maintainer-1
```

정상 상태는 Gateway `healthy`, Poller/Maintainer `running`, 유지관리 로그 `level=ok`다. 50 MiB는 Flarum 200/Gateway 201, 50 MiB+1바이트는 Flarum 422/Gateway 400이어야 한다.

## 보관, 삭제 및 용량 경보

- Artifact는 생성 후 24시간이 지나면 유지관리 컨테이너가 삭제한다.
- 파일 삭제 API는 메타데이터와 원본을 함께 제거한다.
- 디스크 사용률 70%부터 `warning`, 85%부터 `critical` 이벤트를 컨테이너 로그에 남긴다.
- `critical`이면 신규 대용량 첨부를 일시 제한하고 오래된 Artifact, 고아 파일, Flarum 업로드 용량을 순서대로 확인한다.
- Flarum 질문을 삭제하더라도 AI Artifact는 별도 보관 경계에 따라 삭제된다.

## 롤백

Flarum은 적용 시 출력된 백업 경로만 사용한다.

```bash
sudo /usr/local/sbin/techflow-flarum-upload-policy rollback \
  /var/backups/techflow-flarum/issue72-YYYYMMDDTHHMMSSZ
```

TechFlow는 배포 전 `runtime-files.tar.gz`와 `.env`를 복원하고 이전 릴리스 태그로 세 서비스를 다시 만든다. DB 마이그레이션은 없으므로 데이터 스키마 롤백은 필요 없다.

## 장애 처리

| 현상 | 확인 | 조치 |
|---|---|---|
| 413/422 | Nginx/PHP/FoF 실효값 | 바깥 한도 >= 64 MiB, FoF 51,200 KiB 확인 |
| Poller fetch 경고 | 첨부 URL, 시간 초과, 크기 | 외부 URL 금지 확인, 120초/2회 재시도 후 재첨부 안내 |
| 압축 안전 거부 | 파일명, 항목 수, 압축비 | 원본 로그만 다시 압축하도록 안내 |
| Maintainer 재시작 | 모듈 경로, 볼륨 권한 | 이미지 버전과 `/var/lib/techflow-artifacts` 0700/10001 확인 |
| 디스크 warning/critical | `df -h`, 유지관리 로그 | 만료 정리 확인 후 고아 파일 조사, 필요 시 업로드 일시 제한 |

