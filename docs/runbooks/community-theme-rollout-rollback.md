# ABLESTACK Community Theme 적용 및 롤백 Runbook

## 1. 목적과 경계

`ablecloud/community-theme`을 Flarum 1.8.18에 설치하고 검증하는 절차다. 테마는 화면 CSS와 한글 상태 표시만 제공하며 Core, Vendor 원본, DB Schema와 Community 콘텐츠를 수정하지 않는다.

WSL 검증은 `/srv/techflow-flarum-staging/app`만 허용한다. 운영 경로 `/var/www/html` 적용은 별도 승인 후에만 수행한다.

## 2. WSL 예행연습

저장소 자산을 WSL ext4 영역에 복사한 뒤 전체 주기를 실행한다.

```bash
sudo install -d -m 0755 /srv/techflow-flarum-staging/sources/ablecloud-community-theme
sudo rsync -a --delete \
  deploy/flarum/extensions/ablecloud-community-theme/ \
  /srv/techflow-flarum-staging/sources/ablecloud-community-theme/

sudo TECHFLOW_THEME_SOURCE=/srv/techflow-flarum-staging/sources/ablecloud-community-theme \
  bash deploy/flarum/rehearse-community-theme.sh cycle issue73-review
```

주기는 기본 상태 기록, 활성화, 기능 검증, 비활성화 롤백, 콘텐츠 무결성 비교, 재활성화를 순서대로 수행한다. 결과는 `/srv/techflow-flarum-staging/rehearsals/issue-73/<run-id>/result.json`에 남는다.

## 3. 운영 적용 전 점검

- Flarum Core가 1.8.18인지 확인한다.
- DB, `/var/www/html`, Nginx·PHP-FPM 설정을 `/var/backups/techflow-flarum/issue73-<UTC>`에 백업한다.
- `composer.json`, `composer.lock`, `settings.extensions_enabled`를 별도 보관한다.
- `https://community.ablecloud.io` HTTP 200, 로그인, 검색, 작성, 첨부의 기존 기준선을 기록한다.
- TechFlow Community Poller 상태와 GitHub→Chat 보호 서비스 상태를 기록한다.

## 4. 운영 적용 절차

승인된 변경 창에서만 다음 명령을 사용한다. 비밀번호와 API Key는 필요하지 않다.

```bash
sudo install -d -o www-data -g www-data -m 0755 \
  /var/www/html/extensions/ablecloud-community-theme
sudo rsync -a --delete \
  deploy/flarum/extensions/ablecloud-community-theme/ \
  /var/www/html/extensions/ablecloud-community-theme/

cd /var/www/html
sudo -u www-data env COMPOSER_HOME=/tmp/techflow-composer \
  composer config repositories.ablecloud-community-theme path \
  /var/www/html/extensions/ablecloud-community-theme
sudo -u www-data env COMPOSER_HOME=/tmp/techflow-composer \
  composer require ablecloud/community-theme:@dev --with-dependencies --no-interaction
sudo -u www-data php flarum extension:enable ablecloud-community-theme
sudo -u www-data php flarum cache:clear
sudo -u www-data env TECHFLOW_ALLOWED_FLARUM_ROOT=/var/www/html \
  php vendor/ablecloud/community-theme/tools/warm-korean-locale.php /var/www/html
sudo systemctl restart php8.3-fpm nginx
```

이미 설치된 테마의 CSS·Locale·JS만 갱신할 때는 변경 자산을
`/tmp/ablecloud-community-theme-<id>`에 전송한 뒤 경로 제한 배포기를 사용한다.
배포기는 현재 Extension·Vendor·Composer·컴파일 자산·Locale을
`/var/backups/techflow-flarum/theme-<id>`에 먼저 백업하고, 적용 후 서비스와
컴파일 CSS를 검증한다.

```bash
sudo bash deploy/flarum/apply-community-theme-update.sh \
  /tmp/ablecloud-community-theme-<id> \
  theme-<id>
```

## 5. 적용 후 검증

- 외부 HTTPS와 서버 로컬 Host/HTTPS 전달 헤더 점검이 모두 200이어야 한다.
- `public/assets/forum.css`에 `--ablecloud-brand-primary`가 있어야 한다.
- `public/assets/forum-ko.js`가 비어 있지 않고 `core.forum.header.search_placeholder`를 포함해야 한다.
- 데스크톱과 모바일에서 홈, 목록, 상세, 검색, 로그인, 글쓰기, 첨부를 확인한다.
- 데스크톱 첫 화면에서 문서 전체의 `scrollY`가 `0`으로 유지되는지 확인한다.
  Welcome Hero, 좌측 메뉴와 Footer는 고정하고 `.IndexPage-results` 전체가
  스크롤되어야 한다. `최신` 선택 콤보를 포함한 `.IndexPage-toolbar`와 토론
  행이 함께 이동해야 하며 `.DiscussionList` 자체의 `scrollTop`은 `0`을
  유지해야 한다. 우측 영역도 `scrollbar-width: none`과 WebKit 규칙으로
  스크롤바를 표시하지 않는다.
- 좌측 메뉴는 사용자 설정 화면과 같이 고정한다. 높이가 짧아 태그가 모두 보이지
  않을 때 내부 스크롤은 허용하지만 `scrollbar-width: none`과 WebKit 규칙으로
  스크롤바는 표시하지 않는다.
- 토론 목록 바깥 Container와 개별 행에 Card Border·Background·Shadow를
  만들지 않는다. 투명한 평면 피드에서 1px 구분선으로만 행을 나누고,
  작성 정보·제목·첫 글 요약·태그·댓글 수·더보기 기능과 파란색 Hover/Focus
  상태를 유지한다.
- 해결 배지와 대표 카테고리·작성자·작성 시각은 같은 헤더 행에서 서로 겹치지
  않아야 한다. 사용자 아바타는 해결 여부와 관계없이 행 좌측 상단의 본문 경계
  안에 있어야 한다.
- 첫 게시물에 이미지가 있으면 첫 이미지를 데스크톱 124×92px, 모바일 88×72px
  우측 썸네일로 표시한다. 이미지가 없는 글에는 빈 썸네일 영역을 만들지 않으며,
  썸네일은 기존 Store 데이터에서 생성하고 지연 로딩해야 한다.
- 사용자 프로필·설정 화면을 1,150px 폭에서 스크롤했을 때 고정 메뉴 폭이
  280px로 유지되고 메뉴 오른쪽 끝이 본문 왼쪽보다 작거나 같은지 확인한다.
- `Answered`, `Best Answer`, `Select Best Answer` 원문 노출이 없어야 한다.
- 사용자·토의·게시물 수와 첨부 해시가 적용 전과 같아야 한다.

## 6. 즉시 롤백

화면 깨짐, 원문 번역 키 노출, 로그인·작성 장애가 하나라도 발생하면 테마만 비활성화한다.

```bash
cd /var/www/html
sudo -u www-data php flarum extension:disable ablecloud-community-theme
sudo -u www-data php flarum cache:clear
sudo -u www-data env TECHFLOW_ALLOWED_FLARUM_ROOT=/var/www/html \
  php vendor/ablecloud/community-theme/tools/warm-korean-locale.php /var/www/html
sudo systemctl restart php8.3-fpm nginx
```

비활성화 후 외부 HTTPS, 로그인, 검색, 글쓰기와 첨부를 다시 확인한다. Package 삭제나 DB 복원은 테마 비활성화만으로 복구되지 않는 별도 장애가 확인될 때만 수행한다.

## 7. 판정

- GO: HTTP 200, 한글 원문 키 0건, 핵심 기능 정상, 콘텐츠·첨부 불변.
- ROLLBACK: 화면·번역·로그인·작성·첨부 중 하나라도 실패.
- 2026-08-19 운영 적용 완료: 사용자 메뉴 겹침 보완과 Reddit형 평면 피드·게시물
  정보 계층·이미지 썸네일이
  WSL 및 운영에 반영되었으며, 운영 백업은
  `/var/backups/techflow-flarum/theme-reddit-post-thumbnail-20260819T122946Z`에 보존한다.
