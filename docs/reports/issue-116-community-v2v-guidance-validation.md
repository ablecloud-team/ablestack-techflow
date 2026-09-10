# Issue #116 Community Standalone KVM V2V 답변 개선 보고서

## 1. 결론

Discussion #183의 첫 질문은 ABLESTACK Standalone에서 ABLESTACK HCI로 가상머신을 옮기는 방법을 묻는 기능 질문이었다. TechFlow-Assistant는 기능 설명 없이 버전·발생 시각·로그부터 요청했고, 후속 문장 `정상적으로 동작하지 않습니다`에서 `정상적으로 동작`만 찾아 문제가 해결됐다고 잘못 답했다.

AI Gateway 0.16.11에서 기능 질문의 답변 순서, Standalone KVM 가져오기 Source 검색, 부정문 판정과 결정적 기본 답변을 보완했다. 운영 Gateway·Poller에 제한 배포하고 잘못된 AI Post #463을 같은 Post에서 수정했다.

## 2. Source 분석 결과

현재 Diplo Source `678835c2008c47fc32c151196a0dd1a1cc446828`에서 확인한 지원 경로는 다음과 같다.

- UI `ManageInstances.vue`는 KVM→KVM의 `external` 작업을 **원격 ABLESTACK 호스트에서 인스턴스 가져오기**로 제공한다.
- `ImportUnmanagedInstance.vue`는 이 경로에서 `importVm` API를 사용한다.
- `ImportVmCmd`는 외부 Host·KVM Hypervisor·사용자·암호·임시 경로를 입력으로 받는다.
- `UnmanagedVMsManagerImpl.importKvmInstance`는 `ImportSource.EXTERNAL`에서 원격 KVM VM을 조회하고 대상 스토리지로 복사한다.
- `LibvirtGetRemoteVmsCommandWrapper`는 `qemu+tcp://<HOST>/system`으로 연결하며 전원이 꺼진 VM만 가져오기 목록에 포함한다.
- `LibvirtComputingResource.copyVolume`은 원본 호스트의 SSH 22에서 `qemu-img convert -O qcow2`를 실행하고 SCP로 변환본을 복사한다.
- VMware vCenter 원본용 `ablestack_v2k`는 별도 경로이며 QEMU 실행 도구 Source `9d5f543dd0a1ffb83f661b1b7b792f16b0b1d73a`도 `--vcenter` 입력을 요구한다.

따라서 질문의 원본이 Standalone KVM/libvirt라면 VMware용 v2k가 아니라 외부 KVM 가져오기 기능을 안내하는 것이 맞다.

## 3. 구현

- Standalone·KVM·HCI·V2V 조합을 외부 KVM 가져오기 질문으로 분류
- `ImportVmCmd`, `importKvmInstance`, `GetRemoteVmsCommand`, `CopyRemoteVolumeCommand`, `ManageInstances.vue` 등 Source 검색어 추가
- 현재 Diplo Source 동작과 사전 조건을 승인된 로컬 근거로 등록
- 방법·지원 범위 질문은 기능 경로·사전 조건·실행 순서·성공 기준을 먼저 제공
- `정상적으로 동작하지`, `해결되지`, `여전히 오류` 등 부정·진행 실패 표현을 해결 판정에서 제외
- OpenAI가 `PROVIDER_INVALID_RESPONSE`를 반환해도 검증된 V2V 기본 답변을 제공하는 결정적 대체 경로 추가
- `virsh`, `nc`, `qemu-img`, `df` 명령을 설명과 분리한 복사 가능한 코드 블록으로 표시
- Discussion #183 Golden Case와 Community API 통합 회귀시험 추가

## 4. 답변 절차 보완

새 절차는 질문을 방법·장애·후속 실패·해결 확인으로 먼저 구분한다. 방법 질문에는 제품 기능을 먼저 설명하고 장애 자료 요청으로 시작하지 않는다. 사용자가 실패를 보고하면 Source에서 확인된 실패 분기를 설명한 뒤 다음 자료만 요청한다.

- 사용 중인 Diplo 버전과 실제로 선택한 마법사
- 실패한 단계와 화면의 오류 전문
- 원본 VM의 전원 상태
- 대상 HCI 호스트에서 원본의 TCP 16509와 SSH 22 연결 결과
- 원본 호스트의 `qemu-img`와 임시 공간
- 앞 단계가 정상일 때만 관리 서버·대상 Agent 로그

질문자가 해결 답변을 선택할 때까지 같은 Case에서 대화를 유지한다. 관리자·지원 담당자의 일반 답변은 맥락에만 기록하고 명시 호출이 없으면 AI가 다시 답하지 않는다.

## 5. Discussion #183 교정 결과

기존 Post #463을 삭제하거나 새 Post를 만들지 않고 같은 글에서 수정했다. 교정 답변은 다음을 포함한다.

- VMware용 v2k와 외부 KVM 가져오기 구분
- Mold 메뉴 경로
- 원본 VM `shut off` 확인
- 16509·22 연결 확인
- `qemu-img`와 임시 공간 확인
- 서비스·디스크 오퍼링과 네트워크 매핑
- 성공 기준과 원본 보존 원칙
- 실패 시 요청할 정확한 로그 경로와 비밀정보 마스킹

브라우저에서 수정 표시, 전체 답변, 명령 코드 블록과 추가 자료 요청 순서를 확인했다. Case는 `PUBLISHED / WAITING_RESOLUTION`이며 질문자의 다음 결과 또는 해결 선택을 기다린다.

## 6. 검증과 운영 상태

| 항목 | 결과 |
|---|---|
| Conversation·Source 집중 시험 | 71건 통과 |
| Community API V2V 통합 시험 | 통과 |
| WSL ext4 전체 시험 | 356건 통과 |
| 변경 파일 Ruff | 통과 |
| OpenAPI | 39개 Operation |
| Gateway | 0.16.11, Healthy, Restart 0 |
| Community Poller | 0.16.11, Healthy, Restart 0 |
| Poller Pending / Failed | 0 / 0 |
| 교정된 Community Post | #463, Approved |
| Community·Chat | HTTP 200 / 200 |
| 보호 서비스 변경 | 0건 |

첫 비게시 OpenAI 질의는 모든 Source Coverage를 확보했지만 `PROVIDER_INVALID_RESPONSE`로 종료됐다. 이 결과를 반영해 Community V2V 질문은 모델 호출 실패 여부와 무관하게 검증된 기본 절차를 반환하도록 추가 보완했다.

## 7. 배포 정보

- 최종 배포 코드 Commit: `20500f9`
- PR 검증 HEAD: `e35179d`
- 이미지: `techflow/ai-gateway:issue116-0.16.11-20500f9`
- 이미지 ID: `sha256:68f85651fd05e8f2bd2872f880c2819d781dd9dfc7b1352c9743eb2133dc15024`
- 패키지 SHA-256: `97658B4CD891B6C5BB31B1870423415A6B05DBA04AF333B23B24E77926F48D76`
- 백업: `/home/ablecloud/techflow-ai-gateway-backups/issue116-v2v-guidance-20260910T225232Z`
- DB Schema 변경: 없음

## 8. 관련 자산

- Issue #116
- `docs/plans/community-capability-answer-flow.md`
- `docs/evidence/issue-116/discussion-183-v2v-guidance.json`
