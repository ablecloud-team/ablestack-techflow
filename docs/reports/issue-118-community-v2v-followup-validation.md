# Issue #118 Community V2V 후속 질문 개선 보고서

## 결론

Discussion #183의 최신 질문은 Standalone KVM에서 TCP 16509를 여는 구체적인 방법이었다. 기존 처리는 최신 댓글보다 전체 대화에 남아 있는 `Standalone + HCI + V2V` 조합을 먼저 평가해 초기 V2V 안내를 반복했다.

AI Gateway 0.16.12에서 최신 질문 전용 답변을 넓은 대화 기본 답변보다 먼저 적용하고, 초기 V2V 기본 답변은 Assistant 답변이 아직 없는 첫 질문에만 사용하도록 수정했다. 운영 Gateway와 Community Poller에 제한 배포하고 기존 Post #469를 같은 Post에서 교정했다.

## 답변 내용

교정 답변은 다음 내용을 포함한다.

- 16509가 현재 제품의 `qemu+tcp://<호스트>/system` 연결에 쓰이는 암호화되지 않은 libvirt TCP 포트라는 설명
- 원본 Standalone 호스트 SSH 접속 위치와 관리자 권한
- `libvirtd`와 `virtproxyd` 실행 방식 구분
- `/etc/libvirt/libvirtd.conf`와 `/etc/libvirt/virtproxyd.conf`의 정확한 설정 경로
- HCI 관리 IP 하나만 4시간 허용하는 firewalld rich rule
- 원본 LISTEN, 대상 HCI 연결, 원격 VM 목록의 정상 기준
- 작업 후 TCP socket 비활성화와 방화벽 규칙 원복
- 실패 시 필요한 daemon, socket, 방화벽 정책과 시간 범위가 지정된 journal 로그

libvirt TCP는 암호화되지 않으므로 인터넷이나 일반 서비스망에는 열지 않으며, 승인된 관리 IP와 이관 시간으로 범위를 제한하도록 안내했다.

## 프로세스 보완

- 최신 댓글의 직접 질문을 전체 대화 키워드보다 우선한다.
- 구체적인 포트·설정 질문에는 해당 작업만 답하고 초기 기능 절차를 반복하지 않는다.
- 초기 기능 안내용 결정적 답변은 첫 Assistant 답변 전에만 적용한다.
- 실행 안내에는 대상 호스트, 접속 방법, 권한, 정확한 경로, 명령, 정상 기준, 보안 제한과 원복을 요구한다.
- 공개 답변 정리기가 승인된 운영 시스템 경로를 가리지 않도록 회귀시험을 추가했다.

## 검증

| 항목 | 결과 |
|---|---|
| 집중 시험 | 76건 통과 |
| 운영 이미지 전체 기능 시험 | 362건 중 361건 통과, Git 저장소가 없는 배포 호스트의 패키징 계약 시험 1건만 환경상 제외 |
| 이전 WSL Git 작업 트리 전체 시험 | 361건 통과 |
| 새 Golden Case | `COMMUNITY-183-LIBVIRT-TCP-16509-FOLLOWUP-001` 통과 |
| 공개 답변 경로 보존 | 두 libvirt 설정 경로 모두 확인 |
| Community Post | #469, 같은 Post에서 수정 |
| DB 감사 이벤트 | `AUTO_PUBLISHED_CORRECTED` |
| Gateway / Poller | 0.16.12, Healthy, Restart 0 |
| Poller Pending / Failed | 0 / 0 |
| Chat | HTTP 200 |
| 보호 서비스 변경 | 없음 |
| 브라우저 검증 | 완료 |

브라우저에서 Post #469가 16509 구성만 안내하고, `/etc/libvirt/libvirtd.conf`, `/etc/libvirt/virtproxyd.conf`, 제한된 firewalld 규칙, 검증과 원복 절차를 표시하는 것을 확인했다. 기존 초기 V2V 메뉴와 `qemu-img` 안내는 반복되지 않는다.

## 배포 정보

- 코드 Commit: `d2fd8af`
- 이미지: `techflow/ai-gateway:issue118-0.16.12-d2fd8af`
- 이미지 ID: `sha256:d01dcd00893b759c92c6ac430872f932b1fec4860cdf1fe437053ecb19963d44`
- 패키지 SHA-256: `02DD00A4F6934FAC67BE8D309E60C4683CEC6B964D620D8BF20BF7BBCF620371`
- 백업: `/home/ablecloud/techflow-ai-gateway-backups/issue118-v2v-followup-20260911T013416Z`
- DB Schema 변경: 없음

## 참고 자료

- libvirt Remote support: https://www.libvirt.org/remote
- libvirt virtproxyd: https://www.libvirt.org/manpages/virtproxyd.html
- Issue #118
- `docs/plans/community-capability-answer-flow.md`
- `docs/evidence/issue-118/discussion-183-libvirt-tcp-followup.json`
