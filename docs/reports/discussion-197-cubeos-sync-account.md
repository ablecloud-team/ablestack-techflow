# Discussion #197 CubeOS sync 계정 보안 조치 검토

문의는 `ablecube-v4.7.2-260902.x86.64`의 sync 계정에 대해 비밀번호 잠금과 nologin 적용이 가능한지 판단하는 것이다. 제공한 shadow 비밀번호 필드는 `*`이며 점검 도구가 `[locked or disabled user]`를 표시했다. 첫 AI 답변은 이를 일반 장애로 취급해 버전·발생 시각·로그만 요청했다.

## 판단과 근거

- `*`와 단독 `!` 등은 crypt 비밀번호 해시가 아니다. UNIX 비밀번호 인증 불가 상태이며 이 값만으로 약한 해시 알고리즘 사용을 판정할 수 없다. 실제 해시 앞의 `!`는 기존 해시 알고리즘을 그대로 유지한 잠금이므로 별도 판단한다. 빈 비밀번호도 구분한다.
- 기준 환경의 Rocky Linux 9.7에서 `setup-2.13.7-10.el9`가 관리하는 기본 계정은 `sync:x:5:0:sync:/sbin:/bin/sync`이며 `passwd -S sync`는 LK였다. coreutils는 `8.32-39.el9`였다. 이는 고객 호스트 직접 점검이 아닌 CubeOS 기반 배포판의 참고 환경 검증이다. 사용자 답변에는 호스트 OS 명칭을 CubeOS로 사용한다.
- coreutils v8.32 `src/sync.c`는 sync/syncfs/fsync/fdatasync를 호출하며 sync 사용자 계정을 조회하지 않는다. 계정의 로그인 셸을 바꾸는 것과 다른 주체의 sync 명령 실행을 구분한다.
- ABLESTACK Cockpit `ABLESTACK-4.7.2` 태그 `9d294e4d591f855b9a33a39e74763a3c5d7d622e`의 호스트 Python/Shell·서비스 생성 경로에서 sync 사용자 전환, User/Group 지정, 소유자 지정 및 계정 조회 의존성을 확인하지 못했다. `ccvm-backup-sync` 서비스는 User를 지정하지 않은 시스템 서비스다. `multipath_sync.sh`와 PCS의 sync는 동작 인자다.
- 추가 계정 의존성 패턴 점검 범위: Cloud Diplo `678835c2008c47fc32c151196a0dd1a1cc446828`, QEMU 도구 `2564c9cf58eb1ff3c3bfe7a150aeef5968ba9afb`. 별도 도입 자동화나 고객 설치 바이너리 전체의 동작을 보증하는 검증은 아니다.
- 공개 답변은 계정 항목을 유지하며 비밀번호 잠금과 `/sbin/nologin` 적용을 안내한다. 계정 삭제, 비밀번호 생성, 서비스 재시작을 요구하지 않는다. 기관별 점검 통과 여부는 원본 판정 기준을 확인해야 한다.

## 엔진 보완

- sync 계정과 sync/rsync/클러스터 동기화 기능의 이름을 구분하고 제공된 비밀번호 마커를 먼저 설명한다.
- 검토한 4.7.2 범위에서 계정 잠금·nologin 절차와 확인 기준을 제공한다. 실제 해시·다른 제품 버전·LDAP/시간 동기화 문의는 고정 답변에서 제외한다.
- 일반 생성 정책과 검색 근거에도 동일 규칙을 추가한다. 호스트 OS는 CubeOS로 부르고 실제 Rocky Linux 게스트 명칭은 유지한다.
- 검증기의 ‘프로그램’ 중 ‘로그’ 오인식과 한국어 조사가 붙은 `sync:*가` 파싱을 보완한다. 전체 shadow나 실제 해시 공개를 요청하지 않는다.

## 검증

기준 환경의 격리된 계정 파일에 `usermod -R <임시 root> -L -s /sbin/nologin sync`를 실행해 `* → !*`, 셸 변경, UID/GID/home 유지를 확인했다. 기준 호스트의 실제 계정과 coreutils 파일은 변경되지 않았고 sync 명령 실행도 성공했다.

회귀시험, Gateway/Poller 제한 배포 및 실제 게시 결과를 최종 검증 뒤 기록한다. 기존 운영 PR #133의 변경을 보존한 브랜치다.

## 출처

- [shadow 비밀번호 필드](https://man7.org/linux/man-pages/man5/shadow.5.html)
- [usermod 잠금·셸 변경](https://man7.org/linux/man-pages/man8/usermod.8.html)
- [nologin 동작](https://man7.org/linux/man-pages/man8/nologin.8.html)
- [coreutils sync 구현](https://github.com/coreutils/coreutils/blob/v8.32/src/sync.c)
- [ABLESTACK 4.7.2 백업 동기화 서비스](https://github.com/ablecloud-team/ablestack-cockpit-plugin/blob/9d294e4d591f855b9a33a39e74763a3c5d7d622e/python/backup/ccvm_backup.py)
