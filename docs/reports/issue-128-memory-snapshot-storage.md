# Issue #128: VM 메모리 스냅샷 지원 범위 답변 교정

## 확인한 문제

Discussion #190 Post #497의 오류는 `KVM does not support the type of snapshot requested`다. Post #498은 KVM 전체 미지원으로 단정하고 메모리 OFF·Agent 버전·전역 설정을 안내했다. 사용자는 #499에서 메모리 보존이 목적이고 디스크 전용은 성공하며 kvm.snapshot.enabled=true, Agent 8.2.0임을 밝혔다.

첨부 화면은 실행 중 Rocky Linux 9/KVM, 메모리 토글 ON, 일시정지 OFF와 오류를 보여 주지만 기본 스토리지 형식은 표시하지 않는다. 사용자의 기본 스토리지를 RBD 또는 GFS2로 추정하지 않는다.

## 제품 소스 근거

검토한 Diplo snapshot은 10973eeb4d284e2d35c1004b2b3f92e8208f0fd1이다. 고객의 빌드 문자열과 설치 바이너리 전체의 일치를 검증한 것은 아니다.

- VMSnapshotManagerImpl.allocVMSnapshot: getVmSnapshotStrategy(vmId, rootPoolId, snapshotMemory)가 null이면 해당 오류를 발생시킨다.
- DefaultVMSnapshotStrategy.canHandle: volumeDao.findByInstance의 모든 volume.format이 QCOW2여야 한다. 메모리 포함은 상위 관리자에서 VM Running을 요구한다.
- LibvirtCreateVMSnapshotCommandWrapper: internal memory snapshot XML을 생성한다. KVM 전체 메모리 미지원으로 단정하면 안 된다.
- StorageVMSnapshotStrategy: kvm.vmstoragesnapshot.enabled 및 !snapshotMemory 조건. 메모리 경로가 아니다.
- ScaleIOVMSnapshotStrategy: PowerFlex/RAW 전용이며 snapshotMemory=true 거절.
- 추가 제한: 암호화 ROOT의 실행 중 메모리 스냅샷, CLVM, 공유 볼륨 등.
- kvm.snapshot.enabled는 SnapshotManagerImpl의 KVM 볼륨 스냅샷 경로 설정이다. 메모리 포함 지원을 추가하는 설정이 아니다.

## 지원 설명 원칙

| 구성 | 메모리 포함 VM 스냅샷 안내 |
|---|---|
| NFS/SharedMountPoint 등 파일 기반, 연결 볼륨 모두 QCOW2 | 기본 메모리 경로 선택 가능. Running 및 추가 제한 확인 필요 |
| Glue RBD/RAW, RAW 블록, QCOW2+RAW 혼합 | 기본 메모리 경로의 all-QCOW2 조건 불충족 |
| PowerFlex | 전용 전략은 메모리 포함 미지원 |
| CLVM | 별도 VM 스냅샷 제한 존재 |

디스크 전용 VM 스냅샷과 개별 볼륨 스냅샷, 메모리 포함 VM 스냅샷을 구분한다. 디스크 전용 성공을 RAM 보존 가능의 증거로 사용하지 않는다. 메모리 OFF나 VM 정지는 사용자의 메모리 보존 목적을 달성하는 해결책이 아니다.

## 엔진 보완

정확한 오류 및 메모리 목적 후속 질문에 검토된 지원 범위 설명을 제공한다. 관련 Source 근거를 curated reference에 추가하고 일반 생성 정책에도 스토리지 종류·전 볼륨 형식·상태·전략별 판정을 요구한다. 이미 제공된 Agent/전역 설정을 다시 요청하지 않고 ROOT/DATA의 pool type/format만 묻는다.

0.16.16 Gateway/Poller 제한 배포, DB schema 변경 없음. 기존 PR #125/#127의 운영 변경을 보존한다. 백업: /home/ablecloud/techflow-ai-gateway-backups/snapshot190-20260929.

## 최종 검증

- 관련 통합시험 140건 통과 및 실제 Community API의 최초 오류→메모리 목적 후속 회귀시험 1건 추가 통과.
- #499 재요청은 이미 생성돼 있던 #500을 반환했다. 게시 상태만으로 새 코드가 답변을 재생성했다고 판단하지 않고 브라우저 내용까지 확인했다.
- 이전 본문이 남은 것을 확인한 뒤 운영 0.16.16의 검토된 지원 설명 함수로 전체 답변을 생성하여 #500을 같은 글에서 교정했다. draft/response/Assistant Turn도 갱신했다.
- 최종 브라우저에서 QCOW2/RAW/RBD/PowerFlex/CLVM, 두 전역 설정 구분, pool type/format만 추가 요청하는 내용 확인 완료.
- Gateway/Poller Healthy, Restart 0. 보호 서비스 컨테이너 변경 없음.
- Issue #128 / PR #129. PR 병합은 수행하지 않았다. 고객의 실제 pool type/format은 여전히 확인이 필요하며 장애 해결 완료로 처리하지 않았다.

## Glue 표기 재발 방지 (0.16.17)

- 생성 지침에는 Glue 원칙이 있었으나 고정 지원 답변에 Ceph RBD가 남아 있었다. 고정 답변을 Glue RBD로 수정하고 공통 사용자 답변/KB 출력 단계에 표기 정규화를 추가했다.
- 명령어, 코드 블록, 패키지·서비스명, 설정 경로, URL은 실제 식별자를 유지한다. 내부 근거 검색도 원래 upstream 식별자를 유지한다.
- 관련 통합시험 143건 통과. 최종 답변/KB 출력 회귀시험 추가.
- Gateway/Poller 0.16.17 제한 배포 완료. 두 컨테이너 Healthy/Restart 0, DB/vector ready, Poller failed=0. 보호 서비스 Container ID/StartedAt 변경 없음.
- Discussion #190 Post #500을 같은 댓글에서 교정하고 저장된 draft/response/turn도 일치시켰다. 브라우저에서 Glue RBD 확인, 댓글 중복 없음.
- 백업: /home/ablecloud/techflow-ai-gateway-backups/glue190-20260929. PR #129에 반영, 병합은 별도.
