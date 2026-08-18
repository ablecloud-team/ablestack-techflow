# Issue #73 Community 인터페이스 현대화 완료 보고서

## 결론

ABLESTACK 브랜드 기반 Flarum 전용 테마 확장을 구현하고 WSL Ubuntu 24.04의 Flarum 1.8.18 복제 환경에서 활성화, 기능 검증, 비활성화 롤백, 재활성화를 완료했다. 데스크톱 1440x900과 모바일 390x844에서 홈·목록·태그·검색·로그인 화면을 실제 렌더링했으며 한글 원문 번역 키 노출은 0건이었다.

Flarum Core, Vendor 원본, DB Schema와 Community 콘텐츠는 수정하지 않았다. 사용자 39명, 토의 117건, 게시물 305건, 콘텐츠와 첨부 해시는 전체 주기 전후 동일했다. 운영 Community에는 적용하지 않았으며 판정은 **운영 적용 전 Conditional GO**다.

## 완료 범위

| 완료 조건 | 결과 |
|---|---|
| 운영 데스크톱·모바일 기준선 | 1440x900, 390x844 증적 확보 |
| 화면 정보 구조 | 홈·목록·상세·글쓰기·첨부·검색·로그인 정의 |
| AI 답변 상태 구분 | AI 기술지원·추가 확인 필요·최종 해결 가이드 구현 |
| ABLESTACK 전용 테마 | 독립 Flarum Extension 구현 |
| 반응형·접근성·한글 | 자동 계약 8/8, 브라우저 원문 키 0건 |
| 기능 회귀 | 홈·목록·태그·검색·로그인·HTTP 200 통과 |
| 비활성화 롤백 | PASS, 콘텐츠·첨부 해시 불변 |
| 운영 자료 | 설계 MD, Runbook, 보고서 MD/PDF, 발표자료 PPTX/PDF |

## 기준선 분석

운영 Community는 제품 기능은 정상이나 화면 계층이 약하고 목록 행 간격이 좁았다. 모바일에서는 뷰포트 전환 시 탐색 메뉴가 콘텐츠를 덮는 모습과 긴 한글 제목의 가독성 저하를 확인했다. 상세 화면에서는 TechFlow-Assistant 진행 답변과 질문자가 선택한 최종 Knowledge Base가 같은 구조로 보였고 `Answered`, `Best Answer`, `Select Best Answer`가 영문으로 남았다.

운영 기준선은 읽기 전용으로만 수집했다. 질문, 답변, 설정과 서비스는 변경하지 않았다.

## 구현 내용

### 독립 테마 확장

- Package: `ablecloud/community-theme`
- 대상: Flarum Core `^1.8`
- 구현: LESS, Composer Extension, 한글 Locale warm-up
- 미포함: Core Patch, Vendor 원본 수정, DB Migration, 별도 프런트엔드 Framework

ABLESTACK Primary `#155EEF`, Ink `#15253E`, Canvas `#F3F7FC`를 기준으로 헤더, Hero, 탐색, 토의 카드, 게시물, 검색, 로그인, 작성기와 첨부 버튼을 블루 계열로 통일했다. 배경에는 옅은 블루 Gradient를 사용하고 카드에는 14~16px Radius, 블루 계열 경계와 낮은 그림자를 적용했다.

브라우저 계산값으로 상세 게시물 카드는 데스크톱 `21px 25px 23px`, 모바일 `18px 16px 20px`의 내부 여백을 확보했다. 목록 카드의 세로 여백도 데스크톱 20px, 모바일 17px로 늘려 보더와 내용이 붙어 보이지 않도록 조정했다.

환영 Hero는 데스크톱 기준 `361px`에서 `127.89px`로 줄였다. 상단 로고 높이는 `34px`, 타이틀 글자는 `28px`로 맞춰 타이틀이 로고보다 작고 다른 본문 글자와도 지나치게 차이 나지 않게 했다. 왼쪽 카테고리 메뉴는 `190px`에서 `240px`로 넓혔고, 태그 페이지의 `토의 시작` 버튼은 도구 모음 내부 오른쪽 넘침 `0px`로 확인했다.

### 답변 상태

| 상태 | 표시 | 사용자 의미 |
|---|---|---|
| 일반 질문 | 흰색 | 사용자가 등록한 질문과 첨부 |
| AI 기술지원 | 파란색 | 해결을 위해 진행 중인 전문 엔지니어 답변 |
| 추가 확인 필요 | 노란색 | 로그·화면·환경 등 추가 자료가 필요한 상태 |
| 최종 해결 가이드 | 녹색 | 질문자가 해결 답변으로 선택한 Knowledge Base |

상태 표시는 사용자에게 내부 근거 ID, 코드 경로와 검토 절차를 노출하지 않는다. 추가 확인 상태는 TechFlow가 `data-techflow-kind="needs-information"` 또는 전용 Class를 부여할 때 적용된다.

### 한글과 접근성

- 해결됨, 해결 답변으로 선택, 해결 답변 선택 취소, 해결된 답변을 사용자 언어로 표시한다.
- 입력 글자는 16px, 모바일 주요 조작 영역은 44px 이상이다.
- 키보드 `:focus-visible`은 3px 고대비 링을 사용한다.
- `prefers-reduced-motion`에서 애니메이션을 최소화한다.
- Primary/White 4.5:1 이상, Ink/White 12:1 이상, Solution text/background 6:1 이상의 자동 명도 대비 계약을 통과했다.

## WSL 검증 결과

최종 실행 ID는 `issue73-20260818-compact-hero-nav`다.

| 단계 | Theme | HTTP | 사용자/토의/게시물 | 콘텐츠 해시 | 첨부 해시 |
|---|---|---:|---:|---|---|
| 기준선 | Disabled | 200 | 39 / 117 / 305 | `83b236aa...48a8` | `19cdf526...97c` |
| 활성화 | Enabled | 200 | 39 / 117 / 305 | 동일 | 동일 |
| 롤백 | Disabled | 200 | 39 / 117 / 305 | 동일 | 동일 |
| 최종 스테이징 | Enabled | 200 | 39 / 117 / 305 | 동일 | 동일 |

구조화 증적의 모든 항목이 PASS다.

- Flarum Core 1.8.18
- 테마 활성화·비활성화 롤백·재활성화
- 한글 Locale과 `forum-ko.js`
- 반응형·접근성 계약
- 홈·목록·태그·검색·로그인 기능 Smoke
- 사용자·토의·게시물과 첨부 무결성

## 한글 Locale 결함 보완

검증 중 스테이징에서 Symfony Locale Catalogue가 빈 상태로 남아 `core.forum.*` 키가 화면에 노출되는 기존 결함을 재현했다. `php flarum cache:clear` 이후 빈 Catalogue를 제거하고 첫 웹 요청 전에 한국어 Catalogue를 명시적으로 warm-up하는 절차를 테마 자산에 포함했다.

최종 브라우저 검사에서 원문 `core.*` 키는 0건, `forum-ko.js`는 Core 검색 번역과 FoF Best Answer 검색 상태의 `해결된 토론`, `해결된 토론 검색`을 포함했다. 화면 제목은 `ABLESTACK Users Forum`으로 정상 표시됐다.

## 화면 검증

| 화면 | 검증 내용 | 결과 |
|---|---|---|
| 홈 Desktop | 브랜드 Hero, 좌측 탐색, 카드 목록 | PASS |
| 홈 Mobile | 390px, 2줄 제목, 태그 절삭, 44px 조작 | PASS |
| 태그 Desktop | 240px 탐색 폭, 토의 시작 버튼 넘침 0px | PASS |
| 검색 | `콘솔` 입력, 해결된 토론 검색 한글화, 기존 검색 경로 유지 | PASS |
| 로그인 | 한글 사용자명·이메일, 비밀번호, 기억하기, 로그인 | PASS |
| 상세·AI 상태 | 실제 운영 DOM 구조 기반 Selector와 자동 계약 | PASS |
| 글쓰기·첨부 | Composer·FoF Upload 스타일 계약, Issue #72 정책 불변 | PASS |

## 롤백 결과

테마 확장을 비활성화하고 Cache와 한글 Locale을 재생성했을 때 HTTP 200이 유지됐고 콘텐츠·첨부 해시는 기준선과 같았다. 같은 Package를 다시 활성화했을 때도 결과가 동일했다.

롤백은 테마 비활성화만 사용하므로 질문, 답변, 첨부, 계정, 검색과 TechFlow 자동화 상태를 건드리지 않는다.

## 운영 영향과 남은 결정

- 운영 Community 변경: 없음
- GitHub→Chat 보호 서비스 변경: 없음
- TechFlow AI Gateway·Poller 변경: 없음
- 업로드 1 GiB/10 GiB 정책 변경: 없음
- 알려진 Composer 보안 권고: Issue #71에서 관리 중인 Symfony Mailer 1건이며 이번 테마가 새로 추가하지 않음

현재 구현은 Chrome, Edge, Firefox, Safari의 현대 버전을 대상으로 한다. 오래된 브라우저에서는 AI 상태 Badge의 `:has()` 기반 자동 감지가 생략될 수 있으나 질문 읽기와 기본 테마는 유지된다.

## 판정

Issue #73의 설계·구현·WSL 기능 검증·롤백·문서화 조건을 충족했다. 운영 적용은 별도 승인 전까지 수행하지 않는다. 검토자가 운영 반영을 승인하면 Runbook에 따라 테마 확장만 적용하고 같은 검증을 반복한다.
