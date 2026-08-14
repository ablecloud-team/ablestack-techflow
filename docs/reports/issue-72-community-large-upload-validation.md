# Issue #72 Community 대용량 첨부 개선 완료 보고서

## 결론

Issue #72의 구현과 운영 적용을 완료했다. Community는 이미지, 일반 로그, ZIP, GZIP, TAR.GZ를 파일당 50 MiB까지 받으며, TechFlow는 같은 상한으로 다운로드한 뒤 압축 해제 100 MiB, 100개 항목, 20배 압축비 안에서만 분석한다.

운영 시험에서 50 MiB는 Flarum HTTP 200과 Gateway HTTP 201로 통과했고, 50 MiB+1바이트는 각각 422와 400으로 거부됐다. 실제 임시 Discussion #172에 네 종류 로그를 붙인 E2E에서 Artifact 4개가 수집되고 AI 답변이 자동 게시됐다. 시험 글과 업로드는 모두 영구 삭제했다.

## 범위와 결과

| 완료 조건 | 결과 | 증적 |
|---|---|---|
| 현재값/목표값 매트릭스 | 완료 | 본 문서와 운영 Runbook |
| 이미지/텍스트/ZIP/GZIP/TAR.GZ E2E | 완료 | Discussion #172, Artifact +4, 답변 게시 |
| 이해 가능한 거부 안내 | 완료 | 크기, 외부 URL, fetch, unsafe 분리 |
| 압축 폭탄/경로/실행/MIME 차단 | 완료 | 모두 HTTP 400 |
| 보관/삭제/디스크 경보 | 완료 | 24시간, 15분, 70%/85% |
| 자동 Golden Case | 완료 | 전체 회귀 259/259 |
| 운영 적용과 롤백 | 완료 | WSL 적용-원복-재적용, 운영 백업 2종 |

## 현재값에서 목표값으로

| 계층 | 적용 전 | 적용 후 |
|---|---:|---:|
| FoF Upload | 10 MiB | 50 MiB |
| PHP-FPM 파일/요청 | 120/120 MiB | 64/64 MiB |
| PHP-FPM 시간/메모리 | 30초, 60초, 128 MiB | 300초, 300초, 256 MiB |
| Poller | 10 MiB, 30초, 재시도 없음 | 50 MiB, 120초, 2회 |
| Gateway 원본/해제 | 10/20 MiB | 50/100 MiB |
| 유지관리 | 수동 | 15분 주기, 24시간 만료 |
| 디스크 알림 | 없음 | 70% warning, 85% critical |

Nginx 요청 상한 120 MiB는 유지했다. 50 MiB 멀티파트 요청을 충분히 감싸면서 PHP/FoF가 실효 경계를 담당한다.

## 구현

- Poller가 Content-Length를 먼저 확인하고 1 MiB 단위로 읽어 상한을 넘는 본문을 메모리에 계속 받지 않는다.
- Community 외부 URL은 다운로드하지 않는다.
- 일시적 HTTP/네트워크 오류는 최대 2회 재시도하고, 안전 거부는 재시도하지 않는다.
- Flarum이 `application/octet-stream` 또는 `application/force-download`로 전달한 ZIP/GZIP/TAR.GZ는 파일명 기준으로 안전한 허용 MIME으로 정규화한다.
- 각 첨부는 독립 처리된다. 한 파일이 거부돼도 다른 파일과 질문 처리는 계속된다.
- 유지관리 컨테이너가 만료 Artifact를 삭제하고 디스크 수준을 JSON 로그로 남긴다.
- Flarum 적용 스크립트는 설정/파일을 백업하고 apply, verify, rollback을 제공한다.

## 시험 결과

### 자동 회귀

운영 코드와 동일한 PR #65 기반 런타임 오버레이에서 259건 전부 통과했다. 설정 상한, 정확한 경계, Content-Length 선차단, 재시도, 외부 URL, 압축 안전 정책, Community 대화 및 기존 답변 품질 계약이 포함된다.

### 운영 경계와 보안

| 시험 | 기대 | 실제 |
|---|---|---|
| Flarum 50 MiB | 허용 | 200 |
| Flarum 50 MiB+1 | 거부 | 422 |
| Gateway 50 MiB | 허용 | 201 |
| Gateway 50 MiB+1 | 거부 | 400 |
| 경로 이탈 ZIP | 거부 | 400 |
| 중첩 압축 | 거부 | 400 |
| 압축 폭탄 | 거부 | 400 |
| 실행 파일 포함 ZIP | 거부 | 400 |
| PNG MIME 위장 | 거부 | 400 |

Gateway의 50 MiB 일반 로그 정규화는 약 18.5초로 120초 경계 안에서 끝났다.

### 실제 대화 E2E

임시 Discussion #172에 일반 로그, ZIP, GZIP, TAR.GZ를 게시했다. Poller가 네 파일을 모두 수집했고 AI 답변이 자동 게시됐다. 이후 Discussion #170~#172와 FoF 시험 업로드 33개를 관리자 권한으로 영구 삭제했다. DB 재확인 결과 시험 Discussion과 업로드 행은 0건이었다.

## 운영 상태

- Flarum 1.8.18 / FoF Upload 1.8.5
- Gateway `techflow/ai-gateway:issue-72-large-uploads`: healthy
- Community Poller: running
- Artifact Maintainer: running, restart 0
- 최초 유지관리: 만료 Artifact 28개 삭제, 디스크 5%, level=ok
- Flarum 루트: 1006 GiB 중 955 GiB 여유
- TechFlow 루트: 1005 GiB 중 917 GiB 여유
- GitHub→Chat 보호 서비스: `frozen`, guard passed

## 이탈과 보완

1. 운영 Flarum의 `config.php`가 framework helper를 사용해 배포 스크립트의 autoload가 필요했다. 설정 변경 전 실패했고, autoload를 추가해 재검증했다.
2. Flarum 서버에서 공용 HTTPS 주소로 자기 자신을 확인할 때 hairpin timeout이 발생했다. 서비스 검증을 로컬 Nginx와 Host 헤더로 고정했다.
3. Maintainer 스크립트 실행 시 Python 모듈 경로가 빠져 최초 컨테이너가 재시작했다. 실행 경로를 고정하고 새 이미지로 교체해 restart 0을 확인했다.
4. 전체 소스 압축을 기존 배포 디렉터리에 푸는 과정에서 root 소유의 비대상 도구 디렉터리에서 권한 오류가 발생했다. 실행 중 컨테이너는 변경되지 않았고, 이후 대상 파일만 교체하는 최소 범위 배포로 완료했다.

## 롤백

- Flarum: `/var/backups/techflow-flarum/issue72-20260814T174252Z`
- TechFlow: `/home/ablecloud/techflow-ai-gateway/backups/issue72-predeploy-20260814T174430Z`
- DB 스키마 변경: 없음
- WSL: 적용, 검증, 원복, 재적용 통과

상세 명령과 장애 대응은 `docs/runbooks/community-large-uploads.md`를 따른다.

## 판정

Issue #72 완료 조건을 모두 충족했다. 운영 배포 상태는 **GO**다.
