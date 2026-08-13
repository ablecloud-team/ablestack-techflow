# Issue #71 Flarum 1.8.18 업데이트 및 롤백 검증 보고서

## 결론

WSL Ubuntu 24.04 스테이징에서 Flarum 1.8.10을 1.8.18로 업데이트하고 다시 1.8.10으로 복원하는 검증을 최종 패키지 집합으로 두 차례 반복해 같은 결과를 얻었다. 게시물과 첨부를 포함한 업무 데이터는 복원 전후 동일했고, 한글 내부 번역 키 노출은 0건이었다.

운영 반영 판정은 **조건부 Go**이다. 담당자의 명시적 승인, 같은 시점 백업, SMTP 유지 확인, 작업 창 확보 후 실행할 수 있다. 이번 작업에서는 운영 서버를 변경하지 않았다.

## 변경 및 검증 범위

- Flarum Core 1.8.10 → 1.8.18
- Flarum Nicknames 1.8.2 → 1.8.3
- Composer 의존성 사전 계산, Migration, 캐시와 한글 Asset 재생성
- 핵심 Community 기능과 TechFlow 통합 회귀
- DB, 게시물, 첨부 정합성 및 반복 롤백
- 운영 Go/No-Go와 명령형 Runbook

대용량 로그/압축 업로드는 Issue #72, UI 현대화는 Issue #73, 백업·모니터링·잔여 보안 항목은 Issue #74에서 이어간다. PR #65는 이 작업과 분리해 Draft 상태로 유지한다.

## 환경 기준선

| 구분 | 운영 기준선 | WSL 스테이징 |
|---|---|---|
| Flarum | 1.8.10 | 1.8.10 복제 후 1.8.18 검증 |
| PHP | 8.3.6 | 8.3 계열 |
| DB | MariaDB 10.11.13 | MariaDB |
| URL | `https://community.ablecloud.io` | `http://localhost:18080` |
| Mail | SMTP | 외부 발송 비활성 |
| Debug | Off | 최종 Off |

WSL 루트 파일시스템은 약 1TB이며 약 953GB가 남아 반복 Snapshot과 후속 업로드 시험에 충분했다.

## 확장 호환성 판정

| 수준 | 확장 | 결과 |
|---|---|---|
| 기능 검증 | Flarum Core, Korean, FoF Upload, FoF Best Answer | 로그인·글·답글·검색·이미지·솔루션 지정 통과 |
| 부팅/로딩 검증 | Flags, Tags, Approval, Suspend, Markdown, SEO, Sitemap, Anti-spam, Subscriptions, Sticky, Statistics, Mentions, Lock, Likes, Emoji, BBCode, Rich Text | Flarum 정보 조회와 Forum/Admin 로딩 오류 없음 |
| 격리 계약 검증 | FoF Webhooks, OAuth, Pusher, Scout, ChatGPT | 스테이징 외부 발송/연동은 비활성, TechFlow 자동 테스트로 계약 검증 |
| 보안 갱신 | Nicknames | 1.8.3으로 갱신, CVE-2026-30913 제거 |
| 조건부 허용 | Symfony Mailer | 6.1.11 유지, SMTP만 허용 |

## 반복 리허설 결과

| 항목 | validated-cycle-01 | validated-cycle-03 |
|---|---:|---:|
| 1.8.10 → 1.8.18 | PASS | PASS |
| 1.8.18 기능/정합성 확인 | PASS | PASS |
| 1.8.18 → 1.8.10 롤백 | PASS | PASS |
| 업무 DB 복원 일치 | PASS | PASS |
| 첨부 해시 일치 | PASS | PASS |

cycle-02에서 전체 DB 해시 차이가 발견됐고 원인을 조사한 결과, Flarum이 시작될 때 만료된 `access_tokens` 3건을 정상 삭제한 것이었다. 모든 다른 테이블은 동일했다. 이후 성공 기준을 휘발성 인증 토큰과 업무 데이터로 분리했고 cycle-03에서 반복 성공을 확인했다.

## 데이터 정합성

| 지표 | 기준선 | 업데이트 | 롤백 |
|---|---:|---:|---:|
| 사용자 | 39 | 39 | 39 |
| 토론 | 117 | 117 | 117 |
| 게시물 | 305 | 305 | 305 |
| 첨부파일 | 114 | 114 | 114 |
| 첨부 용량 | 25,939,695 bytes | 동일 | 동일 |
| 첨부 SHA-256 | `19cdf526...a97c` | 동일 | 동일 |

## 기능과 회귀 시험

- 한국어 Forum과 Admin 화면에서 내부 번역 키 노출 0건
- AI-Assistant 로그인, 토론 생성, 답글, 검색 통과
- 이미지 업로드와 화면 표시 통과
- Best Answer 지정 통과
- 시험 토론 #166에 게시물 4개와 첨부를 만들고 확인한 뒤 롤백으로 제거
- 현 정책에서 일반 텍스트 첨부 거부는 예상 결과이며 대용량 로그/압축 정책은 #72로 이관
- TechFlow AI Gateway 전체 단위 테스트 216건 통과(4.547초)
- 보호 대상 GitHub→Chat 웹훅 코드는 변경하지 않음

외부 Webhook/OAuth/Pusher/Scout는 스테이징에서 의도적으로 끄고 계약 테스트로 검증했다. 실제 운영 업데이트 후에는 Community 새 글 → AI 답변 → Chat 알림 → 후속 대화 → 솔루션/KB 지정 경로를 배포 후 관문으로 다시 확인한다.

## 보안 검토

`flarum/nicknames`의 CVE-2026-30913은 1.8.3 갱신으로 제거됐다.

`symfony/mailer` 6.1.11에는 Sendmail 인자 주입 취약점 CVE-2026-45068이 남는다. Mailer 6.4는 Flarum 1.8이 사용하는 Illuminate 8 및 Symfony MIME 5.4 제약과 함께 설치할 수 없었다. 운영 메일은 SMTP이므로 현재 경로에는 해당 취약 동작이 사용되지 않는다.

다음 조건을 위반하면 No-Go이다.

- 운영 메일 드라이버가 SMTP가 아님
- 작업 중 Sendmail로 변경됨
- Composer가 검증 집합과 다른 패키지 변경을 제안함

장기 조치는 Issue #74에서 추적한다.

## 최종 상태

- WSL 스테이징: Flarum 1.8.18, Nicknames 1.8.3, Debug Off
- Nginx/PHP-FPM/MariaDB: active
- `http://localhost:18080`: HTTP 200
- 운영 Community: 변경 없음(1.8.10 기준선)
- 판정: **조건부 Go, 운영 승인 대기**

## 승인 후 실행 순서

1. 운영 작업 창과 담당자 지정
2. SMTP 설정 확인
3. 앱·설정·DB·업로드 동시 Snapshot 및 복원 가능성 확인
4. Runbook에 따른 업데이트
5. 자동 점검과 Community/TechFlow 운영 E2E
6. Go이면 유지보수 종료, No-Go이면 즉시 롤백

상세 명령과 판정 기준은 `docs/runbooks/flarum-1.8.18-upgrade-rollback.md`, 기계 판독 증적은 `docs/evidence/issue-71/flarum-1.8.18-validation.json`에 있다.
