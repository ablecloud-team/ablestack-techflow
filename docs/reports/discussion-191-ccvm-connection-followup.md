# Discussion #191 클라우드센터 연결 후속 답변

## 확인한 현상과 원인

- 질문자가 CCVM 배포 뒤 세 호스트에서 동시에 구성을 실행했고 Cube의 클라우드센터 연결 실패를 보고했다. AI의 첫 답변 Post #506은 VM 콘솔 `createConsoleEndpoint`를 중심으로 설명했으나 이 기능은 해당 연결 버튼의 경로가 아니다.
- 후속 Post #507은 `ccvm=true`, `statusResource code=200`, `active=true`, `step8=false`와 화면의 연결 실패 문구를 제공했다. Poller는 이 글을 감지했으나 Gateway가 생성 답변의 실행 안내 기준을 두 차례 통과시키지 못해 `COMMUNITY_RESPONSE_NOT_ACTIONABLE`로 거부했다. Poller에는 Post #507이 pending으로 남고 게시 확인 재시도가 반복됐다.
- 제품 소스 `ablestack-cockpit-plugin`의 `src/features/main.js`는 클라우드센터 연결 버튼에서 `python/url/create_address.py cloudCenter`를 실행한다. 해당 Python 코드는 `ccvm-mngt`를 해석한 뒤 `http://<해석된 주소>:8080`에 HTTP GET을 보내며 요청 예외에 게시된 문구를 반환한다. DNS 해석은 `try` 밖에 있어 이 정확한 문구가 표시됐다면 HTTP 요청 단계의 예외다.
- `src/features/cloud-center-virtual-machine.js`의 `checkPCSOK`는 별도의 Pacemaker 리소스 조회다. `statusResource code=200`과 `active=true`는 CCVM 웹 서비스의 8080 응답을 증명하지 않는다. `main.js`의 `step8`은 `wall_monitoring_status`이므로 `false`를 클라우드센터 연결 실패의 직접 원인으로 취급하지 않는다.

## 보완

- 정확한 클라우드센터 연결 실패 문구가 들어온 후속 질문은 검토한 제품 소스 경로로 답변한다. 세 Cube 호스트 각각의 `ccvm-mngt` 해석과 8080 HTTP GET 결과를 비교하고, CCVM의 Mold 서비스·8080 LISTEN·실패 시각 전후 로그를 확인한다.
- 호스트 접속 방법, 관리자 권한, 읽기 전용 명령, 정상 기준, 비밀정보 마스킹을 답변에 포함한다. 기존에 제공된 리소스 상태는 다시 요청하지 않는다. 원인 미확정 상태에서 서비스 재시작·DB 변경을 권하지 않는다.
- 제품 기능을 설명하는 검증된 경로가 일반 생성 답변의 반복 거부를 피하도록 Gateway에서 우선 적용한다. 다른 장애 유형의 생성 답변 안전성 기준은 유지한다.
- 최초 게시 Post #508을 브라우저에서 확인하면서 기존 공개 답변 정리기가 읽기 전용 `curl`의 제품 서비스 URL까지 가리는 문제를 발견했다. 제품에 고정된 `http://ccvm-mngt:8080/`만 보존하고 다른 내부 URL의 마스킹은 유지한다. 주소 조회 명령도 복사 가능한 코드 블록으로 표시한다.

## 검증 및 운영 적용

- 단위 및 Community API 회귀시험에서 Post #507과 같은 후속 내용이 201로 접수되고 근거에 맞는 새 답변이 만들어지는지 확인한다.
- Gateway/Poller만 제한 배포한 뒤 기존 Post #507이 처리되고 새 AI 댓글이 한 번만 게시되는지 확인한다. 서비스 건강 상태와 보호 서비스의 컨테이너 ID·시작 시각을 비교한다.
- 게시된 답변은 현장 결과를 기다리는 진단 안내다. 실제 세 Cube 호스트와 CCVM의 서비스 상태는 질문자의 환경에서 확인해야 한다.
- 초기 배포 0.16.18 뒤 URL 정리 문제를 교정했고, 브라우저에서 확인한 명령 안내 문구까지 다듬어 0.16.20에 반영한다. 기존 Post #508을 같은 댓글에서 수정한다.

## 검토한 소스

- [Cube 연결 버튼 구현](https://github.com/ablecloud-team/ablestack-cockpit-plugin/blob/a135d77421a912c7a63dbec3b2dae70c189f2753/src/features/main.js)
- [연결 주소 및 HTTP 요청 구현](https://github.com/ablecloud-team/ablestack-cockpit-plugin/blob/a135d77421a912c7a63dbec3b2dae70c189f2753/python/url/create_address.py)
- [클라우드센터 리소스와 VM 상태 조회](https://github.com/ablecloud-team/ablestack-cockpit-plugin/blob/a135d77421a912c7a63dbec3b2dae70c189f2753/src/features/cloud-center-virtual-machine.js)
