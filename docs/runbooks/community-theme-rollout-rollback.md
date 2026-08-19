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
- 운영 적용 전 현재 상태: Conditional GO, 승인 대기.
