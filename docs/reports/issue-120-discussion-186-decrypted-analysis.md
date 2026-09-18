# Discussion #186 암호 제공 후 로그 분석

2026-09-18. 기존 Issue #120 / PR #121의 후속 검토.

## 취급 및 범위

관리자가 제공한 암호를 터미널 비표시 입력으로 사용했다. 암호를 코드·파일·DB·Community 답변에 저장하지 않았다. 전체 11.6GB를 무차별 해제하지 않고 QEMU 대상 VM 로그, 현재 management-server.log, agent.log, messages, qemu-hook.log 다섯 파일만 해제했다. 과거 회전 압축 파일 전체와 Windows 내부 로그는 분석 범위에 포함되지 않는다.

원본에서 선별한 13,931바이트 발췌는 IP와 UUID를 마스킹하여 Artifact `682a5b69-fc7c-4a47-adcf-7680a7e311d0`로 등록했다. SHA-256: `679b1cb8b123a8002b5ef119d26a75b5c50adb55b41b39336b030aaf9efc4fb0`. 로그 파서는 발췌를 누락 없이 읽었다. 이 분석은 운영자가 검토한 결과이며 외부 Provider 자동 분석 성공으로 보고하지 않는다.

## 확인된 시간선

QEMU의 Z 시각은 UTC이며 한국 시각으로 +9시간 환산했다.

| 한국 시각 | 증거 |
|---|---|
| 09-18 04:31:29 | 관리 서버 백업 예약 및 NAS 명령 제출 |
| 04:38:11~12 | 호스트 nasbackup.sh 실행, quiesce=false, backup-begin 성공 |
| 04:41:13 이후 | qla2xxx Abort, DID_TIME_OUT, sdm/sdac/sdu READ I/O error, multipath 경로 실패 |
| 04:42:36.864 | 해당 VM QEMU: Desc next is 3 (원문 09-17T19:42:36Z) |
| 04:46:59~04:47:00 | NAS/libvirt 백업 완료 보고 |
| 04:58:13 | 대상 VM Guest Agent 응답 불가 경고 |

management-server.log의 대상 VM 전원 보고 585건은 00:00:33~09:44:33 모두 PowerOn이었다. 이는 게스트 정상 응답을 보장하지 않는다. 당일 자동 종료를 확정할 근거는 발견하지 못했다. 같은 QEMU 오류는 09-03 04:36, 09-17 04:56에도 기록됐다.

## 소스와 해석

- Diplo `10973eeb4d284e2d35c1004b2b3f92e8208f0fd1`의 LibvirtTakeBackupCommandWrapper/nasbackup.sh: quiesce=true일 때만 guest-fsfreeze를 실행한다. 실제 로그는 false이므로 VSS 동결 해제 누락을 주원인으로 제시하지 않는다.
- QEMU v9.1.0 `hw/virtio/virtio.c`: 다음 descriptor 인덱스가 max 이상일 때 해당 오류를 출력한다. virtio_error는 장치를 broken 상태로 설정하며 장치 처리 중단으로 이어질 수 있다.
- `3`은 디스크 번호가 아니다. 해당 오류 한 줄로 virtio-scsi와 다른 VirtIO 장치를 구분하거나 게스트 드라이버·호스트 QEMU 중 원인 주체를 확정할 수 없다. 배포 패키지의 배포판 패치는 추가 확인 대상이다.
- VM 디스크는 /mnt/glue-gfs의 qcow2이고 virtio-scsi 16 queues 구성이 보인다. 그러나 GFS 장치와 오류 FC LUN의 정확한 매핑은 제공 로그만으로 확정하지 않았다.
- FC 오류와 VirtIO 오류가 겹친 것은 확인된 사실이나 직접 인과관계는 미확정이다. 백업 완료도 복원 가능한 애플리케이션 정합성을 보장하지 않는다.

## 답변 교정과 다음 단계

기존 Post #480을 같은 글에서 갱신하고 대화 DB의 답변·응답·Assistant Turn도 교정한다. 원본 질문 Turn에 복구된 Artifact를 연결하고 ARTIFACT_RECOVERED 감사 기록을 남긴다. 암호 대기·백업 공급자 미확인·quiesce 미확인이라는 이전 안내는 최신 답변에서 제거한다.

우선 확인은 GFS→장치→FC 경로 매핑, multipath 상태와 같은 시각 HBA/FC 스위치/스토리지 지연이다. Windows에서는 VirtIO 드라이버 버전과 관련 System 이벤트만 추가 요청한다. 이미 제출한 호스트 로그와 제품 버전은 재요청하지 않는다. 서비스 일괄 재시작이나 컨트롤러 변경을 확정 해결책으로 제시하지 않는다.

관리자 Chat → 관리자 암호 확보 → 엔진 일회성 전달이라는 후속 자동화 설계는 유지한다. 이번 건은 수동 비밀 입력과 검토를 통해 처리했으며, 자동 비밀 접수 API/CLI 및 자동 복호화 기능이 완성됐다는 의미는 아니다.

참고: https://github.com/qemu/qemu/blob/v9.1.0/hw/virtio/virtio.c
