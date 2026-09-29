# Issue #126: 마이그레이션 옵션 설명 질문 개선

## 문제와 원인

Discussion #189 Post #492는 화면의 두 항목 의미를 물었다. #493은 ABSTAINED로 버전·장애 시각·로그를 요구했다. #494에서 제품 사용 설명임을 명시한 뒤에도 실행 안내 검사 및 진행 판정 실패, Provider 응답 오류로 503 재시도가 이어졌다.

기능 설명은 운영 명령을 반드시 포함해야 하는 질문이 아니다. 기존 진행 판정은 명령 또는 조치 위주여서 새로운 설명도 진전으로 인정하지 못할 수 있었다.

## 검토한 제품 근거

사용자 버전: 4.21.0.0-Mold.Diplo-202609151009. 검토한 로컬 Diplo source snapshot: 10973eeb4d284e2d35c1004b2b3f92e8208f0fd1. 고객 설치 바이너리 전체와 해당 snapshot의 일치 여부를 확인한 것은 아니다.

- ManagementServerImpl.listHostsForMigrationOfVM: 볼륨별 local 여부, cluster 범위와 대상 cluster, usesLocal, storage motion capability, 적합한 pool을 평가한다.
- zoneWideVolumeRequiresStorageMotion: zone managed store의 다른 cluster 이동은 driver.zoneWideVolumesAvailableWithoutClusterMotion에 의존한다.
- MigrateWizard.vue: 호스트 requiresStorageMotion을 예/아니오로 표시한다. migrateWithStorage 토글은 볼륨별 목적지 pool 선택 UI와 migrateto 매핑을 제공한다.
- requiresStorageMigration: host flag 또는 volume mapping이 있으면 true이며, migrateVirtualMachineWithVolume과 migrateVirtualMachine 호출을 분기한다.
- UserVmManagerImpl: 볼륨 mapping과 대상 host를 검증한다. 토글 OFF 자체가 필수 volume migration을 금지하는 조건은 아니다.

따라서 같은 cluster의 공유 storage이면 일반적으로 아니오이지만 그것만이 유일한 기준은 아니다. 일부 volume 이동 필요와 모든 디스크 복사도 구분해야 한다. 아니오 표시 자체가 host 적합성/작업 성공을 보장하지 않는다.

## 엔진 변경

- 정확한 두 UI 항목을 묻는 질문 및 사용 설명이라는 후속 정정에 검토된 설명 경로 제공
- 구체적 마이그레이션 오류 진단과 무관한 후속 질문은 이 경로로 덮어쓰지 않음
- 설명형 후속은 새로운 소스 기반 설명만으로도 진전을 인정하며 동일 설명 반복은 유사도로 제한
- 자료 요청보다 항목의 의미와 상호작용을 먼저 설명하도록 정책 보완
- 검토한 판정/UI/API 근거를 curated reference에 등록
- 공개 설명형 답변의 첫 문구를 장애 해결 절차로 표현하지 않음

## 검증

관련 conversation/community/versioned-assist/responses 통합시험 138건 통과. 옵션 상호작용, 존 범위 예외, 불필요한 로그 요청 없음, 실패 문의 오분류 방지, 명령 없는 설명형 진전 시험을 포함한다.

운영 변경은 Gateway/Poller 0.16.15로 제한한다. DB schema 변경 없음. 기존 미병합 PR #125의 운영 변경을 보존한 후속 PR이다. 백업 경로: /home/ablecloud/techflow-ai-gateway-backups/migration189-20260929.
