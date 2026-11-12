# Community #204 미답변 복구와 시간 범위 검사 보완

관련 Issue: #148. 점검일: 2026-11-12 KST.

## 확인된 원인

[토론 #204](https://community.ablecloud.io/d/204-konsol-bogi-bulga)의 원글560은 모든 VM의 콘솔이 연결중에 머무르고 VM 이동·호스트 libvirtd 재시작 후에도 동일하다고 설명했다. 첨부는 없었다. 운영 Gateway/Poller0.16.28은 healthy, Gateway process/database/vector는 ready였지만 원글은 케이스 생성 전 실행 안내 검사에서 반복 거절됐다. Poller에는 재시도가 누적됐다.

공개 게시 없는 실제 분석 요청에서 `ANSWERED`를 받았고, 다음 안내에 `missing-time-window`만 반환되는 것을 재현했다.

```bash
sudo journalctl -u libvirtd --since '-15 min' --no-pager
```

답변은 최근15분 조회와 별도의 정식 서비스 이름도 포함했다. 검사는 `--since`와 `--until`이 둘 다 있거나 특정 한국어 문구가 있을 때만 시간 범위를 인정했다. [systemd 공식 문서](https://www.freedesktop.org/software/systemd/man/latest/journalctl.html#-S)는 현재 시각 기준 상대 시간을 지원한다. 유효한 과거 상대 시작 시각으로 현재까지 조회하는 안내를 시간 범위 누락으로 거절한 것이 확인된 오탐이다.

다른 생성 시도에는 실행 대상·서비스명 누락도 기록됐다. 그 모든 거절이 오탐이었다고 일반화하지 않으며 해당 검사는 유지한다. 고객 환경 콘솔 장애의 실제 원인은 아직 확인되지 않았다.

## 최소 변경과 시험

`community_actionability_issues`는 `journalctl --since`의 유효한 과거 상대 시간만 추가로 인정한다. `'-15 min'`, `'-15min'`, `'15 minutes ago'`, `-10m` 등이 대상이다. 절대 시작 시각만 있는 경우, 미래·0·불명확한 값, 따옴표 없이 잘못 분리된 인자는 이 예외로 통과시키지 않는다. `--follow`/`-f`는 유한한 스냅샷으로 인정하지 않는다.

서비스명, 접속 예시, 실행 대상, 권한, 정상 기준, 로그 위치와 마스킹 안내 검사는 유지한다. 모델 재작성과 게시 권한 경계를 우회하는 변경이 아니다.

관련9개 모듈의 **285개 회귀시험 통과**. 새 API 시험은 상대 시간 안내가 불필요한 재작성 없이 정상 게시되고 동일 이벤트 재전달에도 한 번만 게시되는지 확인한다. 잘못된 범위·follow·다른 실행 안내 누락은 계속 차단된다.

```text
python -m unittest tests.test_conversation tests.test_community tests.test_community_poller tests.test_store tests.test_postgres_store tests.test_versioned_assist tests.test_chat_assist tests.test_epic4_operations tests.test_responses
```

`git diff --check`도 통과했다. 이전 전체 discover에서 확인된 Windows 임시 파일/ignored 연구 폴더 CRLF 문제는 이 관련 시험 결과와 구분한다.

## 공개 답변 복구

Mold의 [Console.vue](https://github.com/ablecloud-team/ablestack-cloud/blob/b58a48992685d16b61f07e66c04b8c0bad4219b9/ui/src/components/widgets/Console.vue#L49-L69), 승인된 제품 문서의 시스템VM 구조와 관련 KVM wrapper를 검토했다. 관리 화면의 주소 생성과 새 콘솔 창의 연결을 구분하고, 부하 점검 요청 실패를 사용자 콘솔 요청 자체의 실패라고 단정하지 않았다.

운영 엔진 코드를 교체하지 않고 기존 저장·게시 인터페이스로 검토 답변을 복구했다. 기존 운영 검사에서도 통과하도록 명시적 시작/끝 범위와 실행 위치를 포함했다. 직전 원문·공개 상태·기존 답변 유무를 대조하고 일반 답변과 같은 케이스/버전 멱등 marker를 사용했다.

- [답변561, 토론 내2번](https://community.ablecloud.io/d/204-konsol-bogi-bulga/2): 공통 경로, 다른 브라우저/PC, 주소 생성 응답, 새 창 WS 오류, 조건부 콘솔 프록시 상태와 필요한 로그를 안내한다. 이미 실패한 재시작/마이그레이션은 반복 권하지 않는다.
- 공개 게시물은 원글560과 AI 답변561의2개이며 중복 답변은 없다.
- 케이스는 `PUBLISHED / ANSWERED / WAITING_RESOLUTION`이다. 실제 해결 결과가 없어 해결 선택·KB 생성을 하지 않았다.
- 정상 Poller가 게시를 확인해 원글560을 seen으로 처리했고 `pendingPosts=0`, `pendingResolutions=0`이 됐다. 운영 Poller 파일을 직접 수정하지 않았다.

## 기존 대기 #203 마무리

승인된 운영 접속에서 이전 예약의 접근 대기도 해소했다. 설치 이미지 원본과 공개 댓글, Diplo4.3 VM 생성 UI의 TPM 옵션을 다시 확인했다.

- 기존 AI 답변556을 검증된 TPM2.0·EFI/SECURE 안내로 교정했다.
- [기존 KB558](https://community.ablecloud.io/d/203-windows-11-seolci/6)을 같은 위치에서2판으로 갱신했다. TPM이 꺼져 있었다는 단정과 설치가 해결됐다는 오해를 제거하고, 선택된 조언과 실제 성공 보고의 부재를 구분했다.
- 사람의 답변557과 해결 선택 출처는 보존했다. 최종 선택은 기존 KB558이며 공개 게시물은6개로 변하지 않았다. 관련 엔진 보완은 이미 병합된 PR #145의 정책이다.

## 배포 경계

운영 엔진은0.16.28을 유지했다. 서비스 재시작·설정/권한 변경·병합·코드 배포는 하지 않았다. Gateway/Poller와 Activepieces app/worker는 healthy였고 GitHub→Chat 보호 서비스의 컨테이너·시작 시각·재시작 횟수는 점검 전후 같았다. 이를 Chat 전체 실사용 E2E로 해석하지 않는다. 코드 변경은 별도 PR 검토와 승인된 운영 반영이 필요하다.
