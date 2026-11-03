# Discussion #192 초기 설치 재시도 전 iSCSI 분리

요청의 핵심은 초기 설치 단계에서 재설치하기 전 외부 iSCSI 연결을 분리하고 스토리지의 기존 데이터를 보존하는 것이다. CCVM 장애 원인 분석은 이 요청을 대체하지 않는다. 후속 CCVM 상태 요청도 분리 전 사용 여부를 확인하는 하위 단계로 취급한다.

## 확인한 문제

첫 AI 댓글 Post #510은 ABSTAINED 결과를 일반 장애 안내로 표시해 버전·시각만 요청했다. 요청자 Post #511은 Diplo v4.7.2, 발생 시각, 세 호스트의 동시 구성과 CCVM 상태 명령 요청을 제공했지만 Gateway 처리의 503 응답이 반복돼 게시되지 않았다. Poller는 해당 댓글을 pending으로 유지했다.

## 검토 근거

- ABLESTACK-4.7.2 태그: `9d294e4d591f855b9a33a39e74763a3c5d7d622e`.
- `python/gfs/gfs_manage.py`의 `create_gfs`는 강제 PV 생성, VG/LV 생성과 `mkfs.gfs2`를 실행한다. 기존 데이터를 보존할 LUN에 신규 GFS 구성을 적용하는 방법을 안내하면 안 된다.
- 제품 VM 종료 절차는 업무 VM, 시스템 VM, CCVM을 정상 정지한 뒤 클러스터를 정지한다. `pcs cluster stop --all`은 초기 설치 대상 전체를 중단할 수 있는 경우에만 안내하며 강제·destroy 옵션을 사용하지 않는다.
- Open-iSCSI의 node 기록은 IQN·portal·필요시 iface로 특정한다. 대상 로그아웃과 node 기록 삭제, LUN 메타데이터 초기화는 구분한다. OS가 iSCSI로 부팅하거나 같은 세션의 다른 LUN을 사용 중이면 온라인 로그아웃 대상에서 제외한다.

## 반영

초기 설치 목적을 유지하는 검토된 절차를 Gateway에 추가했다. 대상 식별, 사용 정상 정지, 해당 기록의 자동 재연결 방지, 대상 로그아웃, 설치 중 LUN 비노출, 기존 메타데이터 보존 순서로 답변한다. 후속 CCVM 상태 질문에도 이 목표를 유지한다. 버전·시각·장애 로그를 반복 요청하지 않는다.

검색어와 고정 소스 근거를 보강하고 일반 생성 정책에도 동일 목적 유지 규칙을 적용했다. 실행 안내 검증에서 ‘로그아웃’을 ‘로그 수집’으로 인식하던 문제를 수정했다. 초기 설치·후속 목표 유지·iSCSI 부팅 제외·Community API 회귀를 검증한다.

## 운영 검증

- 관련 단위·Community API 회귀시험 195건 통과. 최초 요청 및 CCVM 상태 후속 요청 모두 iSCSI 분리 목표를 유지하고 명령·정지 조건을 제공한다.
- Gateway/Poller 0.16.21 제한 배포. Healthy/Restart 0, process/database/vector ready, Poller pendingPosts=0·failed=0. 보호 서비스 Container ID·시작 시각 변경 없음.
- 보류 중인 Post #511은 정상 Gateway 요청으로 재처리해 답변 Post #512를 한 번 게시했다. 자동 재시도 체크포인트도 이후 확인 완료됐다. 운영자가 확인한 ‘초기 설치 단계’ 범위를 같은 답변에 반영하고 DB의 draft/response/Assistant Turn도 갱신했다.
- 브라우저에서 대상 IQN/portal startup manual 및 logout 명령, 사용 정지 조건, 설치 중 외부 LUN 비노출, 기존 GFS 초기화 금지를 확인했다. 기존 네 게시물 외 중복 댓글 없음.
- 운영 백업: `/home/ablecloud/techflow-ai-gateway-backups/issue132-20261002`. Issue #132 / PR #133. 질문자 환경의 실제 대상 IQN·portal·WWID는 제시한 조회 결과로 특정해야 한다.

## 참고

- [4.7.2 GFS 구성 소스](https://github.com/ablecloud-team/ablestack-cockpit-plugin/blob/9d294e4d591f855b9a33a39e74763a3c5d7d622e/python/gfs/gfs_manage.py)
- [ABLESTACK VM 시스템 정지 절차](https://github.com/ablecloud-team/ablestack-docs/blob/f25e3d652cfcc14e5b794781ead65e54d8de8bfb/docs/administration/system-restart-vm.md)
- [Open-iSCSI 관리 절차](https://github.com/open-iscsi/open-iscsi/blob/master/README)
