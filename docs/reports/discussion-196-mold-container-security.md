# Discussion #196 CCVM overlay 소유권과 NFS 보안 점검

사용자는 Diplo 4.7.2 CCVM의 컨테이너 overlay 파일 소유자 경고와 불필요한 NFS 비활성화 항목을 문의했다. 기존 답변은 해당 경로를 Console Proxy 코드와 연결했고, 실제 CCVM의 NFS 구성 근거 없이 미사용 예외를 안내했다. 운영 경로도 `/제품 내부 경로`로 가려져 점검에 도움이 되지 않았다.

## 검토 결과

- CCVM은 Mold 관리 VM이며 CPVM 콘솔 프록시와 구분한다. 경로만으로 어느 이미지·컨테이너인지 특정할 수 없다.
- `/var/lib/containers/storage`는 root Podman 저장소 기본 경로다. overlay 파일의 숫자 UID/GID와 호스트 NSS 이름 해석 실패를 구분해야 한다. 컨테이너·이미지의 계정과 참조 계층을 함께 확인한 뒤 정상 이미지 소유권, 실제 이미지 결함, 미사용 자원을 구분한다.
- 실행 목록에 없다는 이유만으로 unused 계층으로 판단하지 않는다. 중지 컨테이너와 이미지·공유 계층도 확인한다. 전체 inspect에는 자격 증명이 있을 수 있어 Name/GraphDriver 경로만 필터링한다. 컨테이너의 shadow 내용은 수집하지 않는다.
- ABLESTACK-4.7.2 태그 `9d294e4d591f855b9a33a39e74763a3c5d7d622e`의 `shell/host/ccvm_bootstrap.sh` 62~70행은 `/nfs`, exports, `nfs-server.service`, primary/secondary 디렉터리를 구성한다. 129~132행은 secondary에 시스템 VM 템플릿을 준비한다. 현재 등록된 Mold 저장소가 이 NFS를 사용하면 유지해야 한다.
- `nfsd`는 NFS 서버의 커널·유틸리티 명칭으로 systemd 서비스 이름과 동일하지 않다. 기준 CubeOS 기반 환경의 `nfs-server.service`는 Type=oneshot/RemainAfterExit=yes라 active(exited) 표시가 가능하다. 111은 공용 RPC 포트이므로 단독으로 NFS 사용을 판단하지 않는다.

## 반영

- 숫자 소유자·컨테이너 계층 및 NFS 저장소 의존성을 우선하는 검토된 답변 경로, 생성 정책 및 검색 근거를 추가했다. 이 문의에는 관련 없는 ConsoleAccessManagerImpl·콘솔 부하 래퍼가 검색 우선순위에 끼어들지 않도록 한다.
- 컨테이너 backing layer의 직접 삭제·chown·일괄 prune 또는 사용 중 NFS 비활성화를 안내하지 않는다. 읽기 전용 명령과 결과 해석, 이미지 수정·업데이트 또는 사용 상태에 맞는 보안 증빙 방법을 설명한다.
- 운영 점검에 필요한 overlay 경로와 NFS·legacy 서비스 설정 경로를 공개 답변에 보존한다. 다른 사설 소스 경로의 마스킹은 유지한다.
- 현재 게시된 답변의 동일 Post ID를 교정할 때 근거 원장·citations도 함께 갱신하도록 저장소 처리를 보완했다. 본문·response·Assistant Turn은 일치시킨다. DB 스키마 변경은 없다.

## 검증 및 게시

- 관련 단위·Community API·저장소 회귀시험 221건 통과. 전체·단일 주제 안내, 콘솔 검색 제외, 경로 보존, 동일 본문에 대한 근거 갱신 및 멱등성을 검증했다.
- 기준 환경에서 nfs-server.service의 Type=oneshot, RemainAfterExit=yes를 확인했다. 고객 CCVM의 파일·컨테이너·NFS 설정을 직접 변경하는 작업은 아니다.
- PR #137 병합본을 운영에 반영한 뒤 Discussion #196의 기존 Post #530과 draft/response/Assistant Turn/citations/근거 원장을 함께 교정한다. 최종 운영 검증 이력은 PR #137에 기록한다.

## 출처

- [4.7.2 CCVM 구성 소스](https://github.com/ablecloud-team/ablestack-cockpit-plugin/blob/9d294e4d591f855b9a33a39e74763a3c5d7d622e/shell/host/ccvm_bootstrap.sh)
- [Podman 저장소 기본 경로](https://docs.podman.io/en/latest/markdown/podman.1.html)
- [Podman inspect](https://docs.podman.io/en/latest/markdown/podman-inspect.1.html)
- [NFS 서버 구성](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_and_using_network_file_services/deploying-an-nfs-server_configuring-and-using-network-file-services)
- [Linux nfsd](https://man7.org/linux/man-pages/man7/nfsd.7.html)
