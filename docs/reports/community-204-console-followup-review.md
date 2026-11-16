# Community #204 콘솔 후속 답변 점검

관련 작업: #154 · [Community 토론](https://community.ablecloud.io/d/204-konsol-bogi-bulga)

## 공개 자료에서 확인한 범위

- 최초에는 모든 VM의 콘솔이 연결 중이며, 마이그레이션·호스트 libvirtd 재시작으로 달라지지 않았다는 질문이었습니다.
- 후속 댓글577은 신규 VM의 콘솔은 정상이고 기존 VM만 실패한다고 범위를 좁혔습니다. 댓글579는 정상 신규 VM과 실패 기존 VM이 같은 호스트라고 확인했습니다.
- 댓글573은 브라우저에서 `createConsoleEndpoint` 응답을 찾지 못했다고 보고했습니다. 이것만으로 요청 미발생 또는 특정 서버 구간 장애를 확정할 수 없습니다.
- 최신 AI 댓글580은 새 범위는 반영했지만, 같은 브라우저 자료를 다시 요청하고 내부 구현 이름을 공개했습니다. 이전 댓글576의 관리 서비스 정지·기동 안내도 현재 환경의 정확한 배포 방식이나 서비스 상태를 확인한 조치가 아닙니다.
- 해결 답변은 선택되지 않았습니다. 해결 또는 KB 생성 대상으로 임의 전환하지 않습니다.

### 첨부와 운영 확인의 한계

댓글571의 `log.txt` 첨부 표시를 확인했습니다. 공개 다운로드는403, 파일 메타데이터 조회는401입니다. 승인된 기존 SSH 키 인증도 거부됐습니다. 이전에 제공받은 암호를 파일이나 예약 실행에 재사용하지 않았습니다.

따라서 이번 점검에서는 첨부 원문을 읽거나 운영 Artifact 등록·실패 경고·진행 중 처리 상태를 대조하지 못했습니다. 기존 AI가 설명한 QGA·block I/O 오류를 독립적으로 검증한 사실로 인용하지 않습니다. 같은 게시물의 공개 보완은 인증·진행 중 작업 확인 후에만 시행합니다.

## 검토한 제품·공식 소스

현재 공개 Diplo ref를 확인한 고정 커밋: `ef41707237ba8bea980d0b5752f79d48cdb4e360`. 이는 고객의 실제 설치 커밋을 확인했다는 뜻이 아닙니다.

1. [Console.vue](https://github.com/ablecloud-team/ablestack-cloud/blob/ef41707237ba8bea980d0b5752f79d48cdb4e360/ui/src/components/widgets/Console.vue#L55)는 부모 창에서 API를 호출하고 성공 결과의 URL을 새 창으로 엽니다. 부모 창의 API와 새 창의 실시간 연결은 다른 관찰 위치입니다.
2. [ConsoleAccessManagerImpl](https://github.com/ablecloud-team/ablestack-cloud/blob/ef41707237ba8bea980d0b5752f79d48cdb4e360/server/src/main/java/org/apache/cloudstack/consoleproxy/ConsoleAccessManagerImpl.java#L358)은 endpoint 구성 중 VM의 VNC 주소·포트를 조회하고 티켓과 세션을 구성합니다. endpoint 성공은 이후 화면 전달·인증 성공의 증거가 아닙니다.
3. [ManagementServerImpl](https://github.com/ablecloud-team/ablestack-cloud/blob/ef41707237ba8bea980d0b5752f79d48cdb4e360/server/src/main/java/com/cloud/server/ManagementServerImpl.java#L5893)은 VM의 실제 인스턴스 이름으로 호스트에 조회합니다. 공개 UI의 표시 이름을 libvirt 도메인 이름으로 단정하지 않습니다.
4. [LibvirtComputingResource](https://github.com/ablecloud-team/ablestack-cloud/blob/ef41707237ba8bea980d0b5752f79d48cdb4e360/plugins/hypervisors/kvm/src/main/java/com/cloud/hypervisor/kvm/resource/LibvirtComputingResource.java#L4900)는 현재 libvirt 도메인 XML의 그래픽 포트 정보를 읽습니다. VM별 표시 정보의 읽기 전용 비교가 가능한 다음 단계입니다.
5. [공식 virsh 문서](https://www.libvirt.org/manpages/virsh.html#domdisplay)의 `domdisplay`는 그래픽 표시 URI를 조회합니다. 조회 성공은 실제 VNC 연결의 성공을 검증하지 않으며, 반환 URI의 표시 번호를 임의의 TCP 포트로 해석하지 않습니다.

같은 호스트의 정상 VM이 있다고 모든 공통 구성요소가 정상이라고 단정하거나, 기존 VM만 실패한다고 VNC 암호 오류·포트 조회 오류를 확정하지 않습니다. 해당 소스·버전과 현재 실행 상태를 대조해야 합니다.

## 엔진에서 재현한 공통 원인과 수정

`community_result_advances`는 단일 백틱을 명령 마커로 사용했습니다. 같은 API 요청에 코드 서식만 추가하거나 이미 안내한 명령의 설명만 바꿔도 전체 문장이 달라 새 단계로 통과했습니다. 수정 전 재현시험에서5개 assertion이 실패했습니다.

- API·파일·클래스 이름의 서식만으로 실행 명령으로 인정하지 않습니다.
- 인식하는 CLI 명령 구간을 추출하고 앞선 AI 답변들의 명령과 비교합니다. 같은 명령의 한국어 설명·서식 변경은 새 진단 단계가 아닙니다.
- 새 출력 해석·기능 설명과 실제 신규 명령은 기존 설명/조치 경로를 유지합니다. 이는 명령 실행 허가나 안전성 검사가 아니라 제한된 진행성 휴리스틱입니다.
- 일반·압축·재작성 프롬프트에서 최신 결과로 가설을 갱신하고, 찾지 못한 UI 자료는 소스 근거가 있는 읽기 전용 대안부터 안내하도록 합니다.
- 실제 첨부는 계속 기존 분석 경로로 전달합니다. 이 변경은 첨부를 읽지 않고 고정 답변으로 우회하는 기능이 아닙니다.

## 공개 답변 보완 방향 — 미게시

먼저 같은 호스트에서 신규 VM은 정상이라는 최신 결과를 인정하고, 전체 Mold/호스트 장애로 단정하지 않습니다. 기존 답변의 관리 서비스 정지·기동을 지금 실행할 근거는 부족하므로 일괄 재시작을 반복하지 않도록 정정합니다.

브라우저 API를 찾는 요청을 다시 반복하기 전에, 관리 권한이 있는 담당자가 **두 VM이 실행 중인 동일 CubeOS/KVM 호스트**에 SSH로 접속하도록 안내합니다. 다음은 조회만 하는 대안의 예시이며, 고객의 실제 환경에서 실행한 결과가 아닙니다.

```bash
ssh <ADMIN_USER>@<KVM_HOST>
sudo virsh list --all
```

Mold의 인스턴스 이름과 libvirt 도메인을 대조한 뒤 아래 자리표시자를 각각 실제 정상·실패 도메인으로 바꿉니다. UI 표시 이름이나 임의의 도메인을 선택하지 않습니다.

```bash
sudo virsh domstate '<NORMAL_DOMAIN>'
sudo virsh domstate '<AFFECTED_DOMAIN>'
sudo virsh domdisplay '<NORMAL_DOMAIN>' --type vnc
sudo virsh domdisplay '<AFFECTED_DOMAIN>' --type vnc
```

두 VM이 실행 중인지, 각 VM에서 VNC 표시 URI 조회가 되는지 또는 어떤 오류가 나오는지를 비교합니다. VM별 URI·표시 번호가 다른 것은 그 자체로 오류가 아닙니다. 둘 다 조회되더라도 화면 연결·인증 정상의 증거가 아니므로, 확인된 차이와 재현 결과를 토대로 다음 구간을 좁힙니다. 조회 실패도 곧바로 VNC 암호 문제로 단정하지 않습니다.

도메인 XML 전체, `--include-password`, VNC 암호·접속 토큰·쿠키를 요구하지 않습니다. 출력 공개 시 IP·호스트·VM 식별자와 비밀은 마스킹하고 정상/실패 구분만 유지합니다. 방화벽 전체 해제, 전역 VNC 공개, DB·XML 직접 수정, 전체 서비스 또는 호스트 재시작을 제안하지 않습니다.

첨부 원문과 운영 처리 상태 확인 후 이 절차가 현재 사례에 맞는지 최종 검토하고, 권한이 있는 기존 AI 답변을 같은 위치에서 보완합니다. 새로운 KB나 중복 답변을 게시하지 않습니다.

## 검증·남은 단계

- API/파일명 서식의 거짓 진행 판정, 같은 CLI 재서술, 실제 새 조회 명령, 긴 대화 압축·재작성 보존을 검증합니다.
- 로컬 API 모의 시험에서 반복 답변은 Provider 내부 재작성으로 이동하고, 다시 반복하면503이며 게시하지 않습니다. 유효한 다음 단계는 한 번만 게시되고 같은 요청의 재시도도 중복 게시하지 않습니다.
- Windows 관련12개 모듈335개 시험이 통과했습니다. 추가 로그 시험은 Windows 임시파일 재개방 잠금으로 실패하여 운영 대상과 같은 Linux에서 검증했습니다.
- Windows 컨테이너 계약22개 중1개는 기존의 무시된 `tmp/research` 타사 체크아웃24개 셸 파일의 CRLF를 재귀 탐색해 실패했습니다. 무관한 타사 파일은 수정·삭제하지 않았습니다. 아래 Linux 검증은 추적된 저장소 스냅샷을 대상으로 이 계약을 포함합니다.
- WSL ext4의 격리 소스 스냅샷·검증용 로컬 Git 저장소와 Python3.12에서 전체485개 시험이 통과했습니다. 실제 운영 서비스나 저장소 원격은 변경하지 않았습니다.
- 실제 모델·Flarum 운영 E2E와 첨부 원문 재검증은 완료하지 못했습니다. 예약 작업의 허용 범위에 따라 병합·배포·서비스 설정 변경은 하지 않습니다.
