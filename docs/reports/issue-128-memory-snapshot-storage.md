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
| Ceph RBD/RAW, RAW 블록, QCOW2+RAW 혼합 | 기본 메모리 경로의 all-QCOW2 조건 불충족 |
| PowerFlex | 전용 전략은 메모리 포함 미지원 |
| CLVM | 별도 VM 스냅샷 제한 존재 |

디스크 전용 VM 스냅샷과 개별 볼륨 스냅샷, 메모리 포함 VM 스냅샷을 구분한다. 디스크 전용 성공을 RAM 보존 가능의 증거로 사용하지 않는다. 메모리 OFF나 VM 정지는 사용자의 메모리 보존 목적을 달성하는 해결책이 아니다.

## 엔진 보완

정확한 오류 및 메모리 목적 후속 질문에 검토된 지원 범위 설명을 제공한다. 관련 Source 근거를 curated reference에 추가하고 일반 생성 정책에도 스토리지 종류·전 볼륨 형식·상태·전략별 판정을 요구한다. 이미 제공된 Agent/전역 설정을 다시 요청하지 않고 ROOT/DATA의 pool type/format만 묻는다.

0.16.16 Gateway/Poller 제한 배포, DB schema 변경 없음. 기존 PR #125/#127의 운영 변경을 보존한다. 백업: /home/ablecloud/techflow-ai-gateway-backups/snapshot190-20260929.
