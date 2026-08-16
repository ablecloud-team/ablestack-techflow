# Community 대용량 첨부 운영 Runbook

## 목적

Community 질문에 이미지, 일반 로그, ZIP, GZIP, TAR.GZ를 첨부했을 때 Flarum 수신부터 TechFlow AI 분석까지 같은 정책으로 처리한다. 일반 파일은 파일당 1 GiB 이하, 지원 압축 파일은 파일당 10 GiB 이하를 허용한다.

```mermaid
flowchart LR
    U["사용자"] --> N["Nginx - 요청 11 GiB"]
    N --> P["PHP-FPM - 파일 10 GiB / 요청 11 GiB"]
    P --> F["Flarum - 일반 1 GiB / 압축 10 GiB"]
    F --> C["Poller - 디스크 임시 저장"]
    C --> G["Gateway - 디스크 스트리밍 수신"]
    G --> S["압축 스트리밍 검사 - 최대 해제 100 GiB"]
    S --> E["정규화 근거만 AI에 전달"]
```

## 운영 경계

| 계층 | 기준 | 운영값 |
|---|---|---:|
| Nginx | 요청 본문 상한 | 11 GiB |
| Nginx | 본문/응답 대기 | 7,200초 |
| PHP-FPM | 파일/요청 | 10 GiB / 11 GiB |
| PHP-FPM | 실행/입력/메모리 | 7,200초 / 7,200초 / 512 MiB |
| FoF Upload | 전역 파일 상한 | 10 GiB (10,485,760 KiB) |
| TechFlow Flarum 정책 | 일반/압축 | 1 GiB / 10 GiB |
| Poller | 일반/압축/시간/재시도 | 1 GiB / 10 GiB / 7,200초 / 2회 |
| AI Gateway | 일반/압축 | 1 GiB / 10 GiB |
| 압축 안전검사 | 해제/항목/압축비 | 100 GiB / 100개 / 20배 |
| Artifact | 보관/점검 | 24시간 / 15분 |
| 디스크 | 경고/위험 | 70% / 85% |

1 GiB는 `1,073,741,824`바이트, 10 GiB는 `10,737,418,240`바이트다. 문서와 사용자 안내에서 GB라고 부르더라도 구현과 시험 판정은 이 이진 경계를 사용한다.

## 처리 원칙

- Poller는 첨부를 1 MiB 단위로 전용 볼륨에 내려받고 Gateway로 다시 스트리밍한다. 전체 파일을 `bytes`나 `bytearray`로 만들지 않는다.
- Gateway는 요청을 `.part` 파일에 순차 기록하며 SHA-256을 동시에 계산한다. Content-Length가 상한을 넘으면 본문을 받기 전에 거부하고, 길이를 알 수 없는 요청은 쓰는 중 상한에서 중단한다.
- ZIP/GZIP/TAR.GZ는 항목을 메모리에 펼치지 않고 순차 읽는다. 압축 해제 크기, 압축비, 항목 수, 경로 이탈, 링크·특수 파일, 실행 파일, 중첩 압축을 검사한다.
- AI 질의에는 원본 대용량 파일을 다시 읽히지 않는다. 업로드 때 생성한 비밀정보 제거·요약 근거 파일만 사용하며 해당 근거의 SHA-256을 다시 확인한다.
- 이미지 입력은 종전 이미지 크기·차원 정책을 유지한다. 1 GiB 일반 상한은 이미지 디코딩 상한을 확대한다는 의미가 아니다.

## 허용 및 거부

허용 대상은 PNG/JPEG/WebP 이미지, UTF-8 텍스트 로그와 JSON/CSV/TSV, ZIP, GZIP, TAR.GZ/TGZ다. PDF는 Community 보관은 가능하지만 현재 TechFlow 로그 분석 대상은 아니다.

다음 조건은 안전하게 거부하고 사용자에게 재첨부 안내를 제공한다.

- 일반 파일 1 GiB 초과 또는 지원 압축 파일 10 GiB 초과
- Community 외부 주소
- ZIP/TAR 내부 경로 이탈, 절대 경로, 드라이브 경로
- 심볼릭 링크, 파이프, 장치 등 특수 파일
- 실행 파일 또는 중첩 압축
- 압축 해제 100 GiB, 항목 100개, 압축비 20배 초과
- UTF-8이 아닌 로그, 바이너리 로그, 이미지 MIME 위장

## 적용

Flarum 서버에서 배포 자산을 설치한 뒤 적용한다.

```bash
sudo /usr/local/sbin/techflow-flarum-upload-policy apply
sudo /usr/local/sbin/techflow-flarum-upload-policy verify
```

TechFlow는 런타임 전용 `.env`에 같은 값을 설정하고 다음 세 서비스만 교체한다.

```bash
docker compose -f compose.yml -f compose.openai.override.yml config --quiet
docker compose -f compose.yml -f compose.openai.override.yml up -d --no-deps \
  gateway community-poller artifact-maintainer
```

GitHub→Chat 보호 서비스는 배포 대상이 아니다. 배포 전후에 보호 검사를 실행하고 컨테이너 ID·이미지·시작 시각이 같아야 한다.

```bash
cd /opt/ablestack-techflow/activepieces
sudo python3 scripts/protected_service_guard.py \
  --lock protected-services.json --env-file .env \
  --compose compose.yml --ingress ingress/Caddyfile
```

## 경계 검증

Gateway 전용 시험은 정확한 1 GiB 일반 로그와 정확한 10 GiB ZIP64 파일을 디스크에서 생성·전송한다. 성공 Artifact는 시험 종료 시 삭제하고 생성 파일도 기본적으로 제거한다.

```bash
python scripts/verify_large_upload_boundaries.py \
  --base-url http://127.0.0.1:8090 \
  --workdir /var/tmp/techflow-issue72-boundary \
  --timeout 7200
```

정상 판정은 다음과 같다.

| 시험 | 기대 HTTP |
|---|---:|
| 일반 1 GiB | 201 |
| 일반 1 GiB + 1바이트 선언 | 400 |
| ZIP 10 GiB | 201 |
| ZIP 10 GiB + 1바이트 선언 | 400 |
| Flarum 일반 1 GiB | 200 |
| Flarum 일반 1 GiB + 1바이트 | 422 |
| Flarum ZIP 10 GiB | 200 |
| Flarum ZIP 10 GiB + 1바이트 | 413 |

## 상태 확인

```bash
sudo /usr/local/sbin/techflow-flarum-upload-policy verify
docker inspect techflow-ai-gateway-gateway-1 --format '{{.State.Health.Status}}'
docker logs --tail 20 techflow-ai-gateway-community-poller-1
docker logs --tail 20 techflow-ai-gateway-artifact-maintainer-1
```

Gateway는 `healthy`, Poller와 Maintainer는 `running`, 유지관리 로그는 `level=ok`여야 한다. Poller 볼륨과 Artifact 볼륨에 `.part` 파일이 장시간 남아 있지 않아야 한다.

## 용량 계획과 장애 처리

10 GiB 압축 파일 하나를 처리할 때 Community 원본, Poller 임시본, Gateway 원본이 잠시 공존할 수 있다. 최악의 정상 동시 점유량은 압축 해제 자료를 별도 저장하지 않는 조건에서도 약 30 GiB이므로, 동시 업로드 수와 24시간 보관량을 포함해 여유 공간을 잡는다.

| 현상 | 확인 | 조치 |
|---|---|---|
| 413/422 | Nginx/PHP/FoF/TechFlow 정책 | 11G, 10G, 10,485,760 KiB 및 종류별 1/10 GiB 확인 |
| Poller fetch 경고 | 첨부 URL, 시간 초과, 임시 볼륨 | 외부 URL 차단과 7,200초/2회 재시도 확인 |
| 압축 안전 거부 | 항목 수, 경로, 해제 크기, 압축비 | 로그만 담아 다시 압축하도록 안내 |
| 디스크 warning/critical | `df -h`, Maintainer 로그, `.part` | 만료/고아 파일 정리 후 신규 대용량 첨부 일시 제한 |
| 처리 지연 | Gateway CPU, `VmHWM`, 업로드 경과 시간 | 동시 처리 수를 낮추고 큐 기반 비동기 분석을 후속 검토 |

## 롤백

Flarum은 적용 시 출력된 백업 경로만 사용한다.

```bash
sudo /usr/local/sbin/techflow-flarum-upload-policy rollback \
  /var/backups/techflow-flarum/issue72-YYYYMMDDTHHMMSSZ
```

TechFlow는 배포 전 런타임 파일과 `.env` 백업을 복원하고 이전 릴리스 이미지로 Gateway, Poller, Maintainer만 다시 만든다. DB 스키마 변경은 없다.
