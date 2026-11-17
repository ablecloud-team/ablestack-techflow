# Community #207 HA 자격 근거 점검

관련 Issue: #152. 제안 엔진 버전: 0.16.31. 운영 게시·배포를 완료한 보고서가 아니다.

## 실제 공개 자료 확인

[토론 #207](https://community.ablecloud.io/d/207-ha-hwalseonghwa-jung-host2beonman-lneligible-sangtae-munje)은 원글566, 첫 AI567, 질문자 해결 보고568, AI569, 선택된 KB570의5개 공개 댓글로 구성된다. 사람의 별도 기술지원 답변은 없다. 최초 등록은2026-11-13 KST이므로 예약 범위에 포함된다.

첨부 PNG를 직접 확인했다. Host2는 VM0/0·Ineligible이며 다른 호스트도0/0인데Available이다. 질문자는 VM이1개씩 필요하다는 점을 알고 해결했다고 보고했다. 이 보고는 보존하되, 화면 숫자와 보고만으로 모든 환경의 최소 VM 수 또는 특정 자격 탈락 항목을 확정하면 안 된다. 고객의 IP·실제 호스트명·세부 빌드 문자열은 이 문서에 재기록하지 않는다.

현재 KB는 생성·선택까지 완료됐지만 VM 배치와 하트비트 자격의 관계 및 확인하지 못한 조건을 더 분명히 구분할 필요가 있다. 후속 AI 답변의 유지보수·재기동 관련 일반 권고도 이번 해결 결과에 필요한 조치인지 구분해야 한다.

## 검토한 정확한 소스

- [KVMHAProvider.isEligible](https://github.com/ablecloud-team/ablestack-cloud/blob/ef41707237ba8bea980d0b5752f79d48cdb4e360/plugins/hypervisors/kvm/src/main/java/org/apache/cloudstack/kvm/ha/KVMHAProvider.java#L54-L63): OOBM, 유지보수/사용 상태, 이웃 호스트, 스토리지 하트비트 등을 함께 검사한다.
- [hasStoragePoolHeartbeatEnabled](https://github.com/ablecloud-team/ablestack-cloud/blob/ef41707237ba8bea980d0b5752f79d48cdb4e360/plugins/hypervisors/kvm/src/main/java/org/apache/cloudstack/kvm/ha/KVMHostActivityChecker.java#L213-L222): 호스트에서 확인된 볼륨/풀 중 하트비트가 활성화된 대상이 있는지 확인한다.
- [getVolumeUuidOnHost/getNeighbors](https://github.com/ablecloud-team/ablestack-cloud/blob/ef41707237ba8bea980d0b5752f79d48cdb4e360/plugins/hypervisors/kvm/src/main/java/org/apache/cloudstack/kvm/ha/KVMHostActivityChecker.java#L295-L330): 호스트에 연결된 VM과 볼륨에서 풀을 찾고 클러스터의 다른Up KVM/LXC 호스트를 확인한다.

이 검토 커밋을 고객의 실제 배포 커밋과 동일하다고 주장하지 않는다. 화면의 VM 개수와 내부 VM·볼륨·풀 목록의 관계, 당시 자격 조건별 값은 확인되지 않았다. 따라서 배치 조정이 하트비트 대상 탐색에 영향을 줄 수 있다는 소스 설명과 이번 고객 환경에서 실제 어느 조건이 바뀌었는지는 구분한다.

## 재현한 검색 누락과 최소 변경

원 제목의 `lneligible` 표기를 유지한 질문과 적합한 HA 소스 형태의 후보2개를 시험했다. 수정 전 검색어 확장은 빈 값이고 관련성 필터는 두 후보를 모두 제외했다. 이것이 최초 운영 ABSTAINED의 유일한 원인이라고 단정하지는 않는다.

호스트 HA 문맥에 `KVMHAProvider`, `KVMHostActivityChecker`, `getNeighbors`, `hasStoragePoolHeartbeatEnabled`, `getVolumeUuidOnHost` 등의 검색어를 추가하고 해당 코드의 우선순위를 높인다. 원문의 enum을 바꾸거나 실시간 상태를 추정하는 동작은 아니다. 무관한 VM HA·콘솔·NTP 질문은 기존 경로를 유지한다. UTF-8 검색 예산도 유지한다.

KB 종합 지침에는 조치 후 개선 보고와 검증된 근본 원인/일반 필수 조건을 구분하고, 첨부의 반례와 확인하지 못한 적용 범위를 명시하도록 추가했다. 특정 VM 개수를 무조건 부정하거나 모든 버전에서 동일하다고 하드코딩하지 않는다.

## 운영 교정안 — 미게시

기존 KB570을 새 글로 복제하지 않고 같은 위치에서 다음과 같이 보완할 계획이다.

- 질문자가 VM 배치 관련 사항을 확인해 해결했다고 보고한 결과는 그대로 기록한다.
- 호스트 HA 자격이 UI의 VM 숫자만으로 결정되는 단일 조건은 아니며 원격 전원 관리, 호스트 운영 상태, 같은 클러스터의 이웃과 스토리지 하트비트 조건을 함께 본다는 범위를 설명한다.
- VM 볼륨으로 하트비트 대상 풀을 찾는 구현이 있으므로 배치가 영향을 줄 수 있지만, 이번에 실제 어느 조건이 바뀌었는지는 미확인이라고 구분한다.
- 같은 첨부에서 다른 VM0/0 호스트가Available인 사실을 반영하고, "모든 호스트에 사용자 VM1대가 절대 조건"으로 일반화하지 않는다.
- 현재 해결 상태를 유지한다면 불필요한 서비스 재시작·라이브 마이그레이션·전원 차단 시험을 새로 권하지 않는다. 호스트 HA와 VM의 HA 제공 오퍼링도 구분한다.

사람의 글과 기존 해결 선택을 수정하지 않는다. 운영 케이스·현재 원문·첨부 등록/실패 경고를 대조한 뒤 필요한 AI569/KB570만 교정하고 공개 내용과 최종 선택을 재확인해야 한다.

## 미완료 경계

기존 SSH 키 인증이 거부되어 새 승인 세션/런타임 인증 경로를 요청했다. 엔진의 첨부 등록·실패 경고와 처리 상태, 기존 AI/KB 공개 편집은 아직 검증하지 못했다. 로컬 체크포인트는 완료로 기록하지 않는다. 개선 PR만 등록하며 예약 작업에서 자동 병합·운영 배포·권한/서비스 설정 변경은 하지 않는다.
