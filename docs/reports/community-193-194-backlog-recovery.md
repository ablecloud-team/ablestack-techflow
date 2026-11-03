# Community #193·#194 대기 항목과 재설치 답변 복구

## 확인한 실제 상태

- #193 공개 페이지와 인증 API의 토론·원글 Post #514는 모두 404였다. 접근할 수 없는 원문을 복원하거나 새 답변을 게시하지 않는다. Poller에는 해당 이벤트의 확인 재시도가 남아 있었다.
- #194 자체는 공개 상태이며 이미 해결 답변과 KB가 있었다. 대기 항목 Post #522는 number 8, isHidden=true, hiddenAt=2026-10-07T02:26:54Z였다. 이 숨긴 댓글을 다시 처리·게시하면 안 된다.
- #194 공개 요청자 Post #517은 VM Cube, 모든 스토리지 공 디스크, 보존 불필요를 명시했다. Post #519는 GFS iSCSI·마운트를 해제했지만 VM 정지 여부를 확인하지 않았다고 했다.
- 기존 최신 AI 답변 Post #520과 선택된 KB Post #521은 보존·복원 절차로 목표를 바꾸었다. 이는 요청자의 명시적 초기화 목표와 맞지 않는다. 두 게시물을 같은 위치에서 교정한다.
- 공개 본문과 저장된 요청자 Turn에는 첨부가 없었다. 숨긴 Post #522의 내용은 분석하거나 재게시하지 않고 가시성 메타데이터만 확인했다.

## 엔진 보완

- Poller는 오래된 미확인 항목에 대해 인증된 Flarum 가시성을 확인한다. 최소 30초 간격 두 번의 NOT_FOUND/HIDDEN 관측 뒤 pending에서 retiredPosts로 이동하고 이유·시각만 보존한다. 401/403·전송 오류·5xx와 새 대기 항목은 취소로 판정하지 않는다. 숨긴 토론도 발견 대상에서 제외한다.
- Gateway는 큐에서 늦게 도착한 댓글도 생성 전에 다시 확인해 접근 불가·숨김·미승인 원문을 답변으로 되살리지 않는다. 전송 오류는 취소하지 않고 재시도한다.
- 데이터 보존·초기화 목표는 요청자의 발언 순서에서 추출한다. Assistant의 보존 권고가 요청자의 초기화 목표를 덮어쓰지 못하게 한다. 명시적 목표 변경은 최신 요청자 발언을 따른다.
- 공유 LUN 초기화 후 재설치 절차와 VM 정지 확인 전 분리한 경우의 다음 점검을 제공한다. 장치 이름을 추정한 wipe 명령이나 일괄 로그인·강제 종료를 제시하지 않는다. VM Cube 전용 설치 문서와 GFS 구성 소스를 우선한다.
- 절차형 KB는 요청·현재 상태와 절차 판단을 표시하고 명령을 코드 블록으로 보존한다. 실제 작업 완료를 단정하지 않는다. 기존 KB를 같은 Post ID로 교정할 때 Assistant Turn도 함께 갱신한다.

## 원 게시물 보완 방향

#194는 전체 소비자 정지 확인 → 대상 LUN 확인·초기화/재생성 → OS 설치 중 외부 LUN 비노출 → CubeOS 설치 → 새 빈 LUN의 GFS·CCVM 신규 구성 순서로 정리한다. 이미 스토리지를 끊었다면 가동 VM·클러스터 상태 확인이 우선이다. 실제 초기화 명령·장비 메뉴는 모델과 WWID 등의 대상 대조가 필요하다. 기존 해결 표시와 선택된 KB Post ID는 유지하며 실제 작업 완료로 해석하지 않는다.

## 검증 및 운영

회귀시험, 기존 답변·KB 교정, 가시성 기반 대기 해소와 병합본 운영 반영을 검증한 뒤 PR에 증적을 기록한다. #198 등 새 질문의 대기 항목과 별도 #184 해결 확인 대기는 이 요청의 수동 처리 범위에 포함하지 않는다.

## 근거

- [VM Cube 전용 설치 가이드](https://github.com/ablecloud-team/ablestack-docs/blob/f25e3d652cfcc14e5b794781ead65e54d8de8bfb/docs/getting-started/install-guide-general-virtualization-cube.md)
- [ABLESTACK VM 시스템 종료 순서](https://github.com/ablecloud-team/ablestack-docs/blob/f25e3d652cfcc14e5b794781ead65e54d8de8bfb/docs/administration/system-restart-vm.md)
- [GFS 신규 생성 소스](https://github.com/ablecloud-team/ablestack-cockpit-plugin/blob/9d294e4d591f855b9a33a39e74763a3c5d7d622e/python/gfs/gfs_manage.py)
