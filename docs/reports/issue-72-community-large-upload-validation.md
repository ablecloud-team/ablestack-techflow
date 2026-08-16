# Issue #72 Community 대용량 첨부 개선 완료 보고서

## 결론

Issue #72의 대용량 첨부 정책을 일반 파일 1 GiB 이하, 지원 압축 파일 10 GiB 이하로 확대하고 운영 Flarum과 TechFlow AI Gateway에 적용했다. 정확한 경계 크기의 실파일을 사용한 운영 시험에서 일반 파일 1 GiB와 ZIP 10 GiB는 수용됐고, 각각 1바이트 초과 파일은 거부됐다.

대용량 파일은 Poller와 Gateway가 디스크 기반으로 스트리밍하며, AI에는 원본 전체가 아니라 업로드 시 생성한 비밀정보 제거·요약 근거만 전달한다. 10 GiB 압축파일을 실제로 Gateway에서 분석했을 때 프로세스 최대 상주 메모리는 약 60.3 MiB였다. 시험 첨부, Artifact, 컨테이너, 볼륨과 임시 파일은 모두 삭제했고 운영 DB 잔존은 0건이다.

## 완료 범위

| 완료 조건 | 결과 |
|---|---|
| 일반 파일 최대 1 GiB | Flarum 200, Gateway 201 |
| 지원 압축 파일 최대 10 GiB | Flarum 200, Gateway 201 |
| 각 상한 +1바이트 거부 | Flarum 422/413, Gateway 400/400 |
| 디스크 기반 스트리밍 | Poller 임시 볼륨, Gateway `.part` 파일 |
| 압축 안전 정책 | 최대 해제 100 GiB, 100개 항목, 20배 압축비 |
| 자동 회귀 | 263/263 통과 |
| 운영 적용·롤백 자산 | 적용/검증/롤백 스크립트와 백업 확보 |
| 보호 서비스 불변 | `github-chat-v1 state=frozen guard=passed` |

## 계층별 운영값

| 계층 | 적용 전 | 적용 후 |
|---|---:|---:|
| Nginx 요청 | 120 MiB | 11 GiB, 7,200초 |
| PHP-FPM 파일/요청 | 120/120 MiB | 10/11 GiB |
| PHP-FPM 시간/메모리 | 30/60초, 128 MiB | 7,200/7,200초, 512 MiB |
| FoF Upload | 50 MiB | 전역 10 GiB |
| Flarum 유형 정책 | 50 MiB | 일반 1 GiB / 압축 10 GiB |
| Poller | 50 MiB, 120초 | 일반 1 GiB / 압축 10 GiB, 7,200초 |
| Gateway 원본/해제 | 50/100 MiB | 일반 1 GiB / 압축 10 GiB / 해제 100 GiB |

구현 판정은 1 GiB=`1,073,741,824`바이트, 10 GiB=`10,737,418,240`바이트를 사용한다. 사용자 안내에서는 이해하기 쉽게 1GB·10GB라고 표시할 수 있으나 경계 시험과 코드 상수는 이진 단위로 고정했다.

## 구현 내용

- Poller는 Flarum 첨부를 1 MiB 단위로 전용 임시 볼륨에 내려받고 Gateway로 다시 스트리밍한다.
- Gateway는 요청을 `.part` 파일에 순차 기록하면서 SHA-256을 계산한다. 알려진 Content-Length가 상한을 넘으면 본문 전송 전에 거부한다.
- ZIP, GZIP, TAR.GZ는 메모리에 한 번에 펼치지 않고 순차 검사한다. 경로 이탈, 링크·특수 파일, 실행 파일, 중첩 압축과 압축 폭탄을 거부한다.
- 대용량 원본은 AI 질의 때 다시 파싱하지 않는다. 업로드 때 만든 정규화 근거 파일의 해시를 확인한 뒤 필요한 내용만 전달한다.
- 이미지 입력의 기존 크기·해상도 정책은 유지한다. 일반 파일 1 GiB 상한이 이미지 디코딩 상한을 확대하지 않는다.
- Flarum 배포 스크립트는 실제 Nginx `server_name`이 운영 도메인과 다르더라도 단일 활성 사이트인 경우 안전하게 해당 사이트를 선택한다.

## 시험 결과

### 운영 Flarum 실파일 경계

| 시험 | 바이트 | HTTP | 경과 | 저장 결과 |
|---|---:|---:|---:|---|
| 일반 파일 정확히 1 GiB | 1,073,741,824 | 200 | 16초 | 생성 후 204 삭제 |
| 일반 파일 1 GiB+1 | 1,073,741,825 | 422 | 12초 | 생성 0건 |
| ZIP 정확히 10 GiB | 10,737,418,240 | 200 | 410초 | 생성 후 204 삭제 |
| ZIP 10 GiB+1 | 10,737,418,241 | 413 | 227초 | 생성 0건 |

Flarum DB의 시험 업로드 ID 150·151은 삭제 후 0건이며, `public/assets/files`에도 시험 파일이 남아 있지 않다. 업로드 임시 영역과 루트 파일시스템에는 955 GiB가 남아 있다.

### Gateway 독립 경계

| 시험 | HTTP | 경과 | 판정 |
|---|---:|---:|---|
| 일반 파일 정확히 1 GiB | 201 | 27.751초 | PASS |
| 일반 파일 1 GiB+1 선언 | 400 | 선차단 | PASS |
| ZIP 정확히 10 GiB | 201 | 294.814초 | PASS |
| ZIP 10 GiB+1 선언 | 400 | 선차단 | PASS |

성공 Artifact 두 건은 HTTP 200으로 삭제했다. 10 GiB 분석 중 프로세스 `VmHWM`은 61,732 KiB로 약 60.3 MiB였다.

### 자동 회귀와 보안

PR #65 기반 런타임 오버레이에서 263건 전부 통과했다. 일반/압축 상한, 스트리밍 수신, Content-Length 선차단, 재시도, 외부 URL 차단, 압축 안전 정책, Community 대화와 기존 답변 품질 계약을 포함한다.

경로 이탈 ZIP, 중첩 압축, 압축 폭탄, 실행 파일 포함 ZIP, 이미지 MIME 위장은 모두 HTTP 400으로 차단된다.

## 운영 상태

- Flarum 1.8.18 / FoF Upload 1.8.5 / 업로드 정책 검증 통과
- Gateway `techflow/ai-gateway:issue-72-large-uploads-1g10g`: healthy
- Community Poller: 반복 처리 `failed=0`
- Artifact Maintainer: `level=ok`, 디스크 사용 5%, 약 983.2 GB 여유
- Flarum 루트: 1006 GiB 중 955 GiB 여유
- GitHub→Chat 보호 서비스: 배포 전후 `frozen`, guard passed
- Activepieces app/worker/event-gateway/ingress/Redis/Postgres 컨테이너 ID 불변

초기 Poller는 새 Gateway가 준비되기 전에 두 번 `URLError`를 기록했지만, Gateway가 healthy가 된 뒤 반복 처리에서 `failed=0`으로 정상화됐다.

## 배포와 롤백

Flarum 정책 적용 전 백업은 `/var/backups/techflow-flarum/issue72-20260816T010617Z`에 있다. TechFlow 배포 전 백업은 `/home/ablecloud/techflow-ai-gateway/backups/issue72-1g10g-predeploy-20260816T010000Z`에 있으며 런타임 파일과 권한 0600의 환경 파일을 포함한다.

TechFlow는 Gateway, Community Poller, Artifact Maintainer만 재생성했다. Activepieces와 GitHub→Chat 구성은 배포 대상에 포함하지 않았다. DB 스키마 변경은 없다.

## 정리 결과

- Flarum 시험 첨부 2건 삭제, 초과 파일 저장 0건
- Gateway 시험 Artifact 2건 삭제
- TechFlow 경계 시험 컨테이너 6개와 볼륨 7개 삭제
- 1 GiB/10 GiB 실파일과 임시 소스·작업 디렉터리 삭제
- 운영 백업은 롤백 자산으로 유지

## 판정

일반 파일 1 GiB와 지원 압축 파일 10 GiB 요구사항, 초과 거부, 스트리밍 처리, 운영 배포, 보호 서비스 불변과 정리 기준을 모두 충족했다. 운영 판정은 **GO**다.
