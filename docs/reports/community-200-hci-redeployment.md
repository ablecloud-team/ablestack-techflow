# Community #200 HCI 초기 구축 재시도 답변 보완

## 확인한 내용

2026년 11월 4일 한국시간 기준 공개 토론 등록 시각을 최신순으로 대조했다. 범위에 들어온 #200(10:58:18)은 질문자 글 두 건과 AI 답변 한 건으로, AI 답변만 있는 점검 대상이다. 다음 토론 #199는 전날 등록이므로 제외했다. #200은 해결 답변이 선택되지 않았으므로 KB 등록이나 해결 표시 변경 대상이 아니다.

#200의 기존 답변은 초기화·재배포 방법 문의에 오류 시각과 장애 로그부터 요청했다. 질문자는 후속 댓글에서 4.7.4와 재배포 목적을 이미 밝혔다. 제품 버전이나 장애 시각을 다시 요청하지 않고, 지원되는 재배포 경로와 데이터 보존 경계를 설명한다.

## 확인한 제품 동작

- [CCVM 초기화, ABLESTACK 4.7.4](https://github.com/ablecloud-team/ablestack-cockpit-plugin/blob/bede43598910ec2367986b6cd424245e30f77cc7/python/vm/reset_cloud_center.py#L60-L99): HCI 분기는 클라우드센터 리소스 제거와 장애조치 클러스터 해체, 존재하는 Glue RBD CCVM 이미지 삭제, 도메인·설정 정리를 포함한다. VM 재시작이나 SCVM 초기화와 동일하지 않다.
- [SCVM 삭제, ABLESTACK 4.7.4](https://github.com/ablecloud-team/ablestack-cockpit-plugin/blob/bede43598910ec2367986b6cd424245e30f77cc7/python/scvm_status/scvm_status_update.py#L89-L112): VM 정의와 호스트 Glue 설정에 영향을 준다. UI가 막힌 상태를 백엔드 호출로 우회하는 방법은 안내하지 않는다.
- [Cube HCI 운영 가이드](https://github.com/ablecloud-team/ablestack-docs/blob/50d50ad6c8c548dc58db866ca28b4cbb43cc74d0/docs/admin-guide/cube/cube-admin-guide-ablestack-hci.md#L407-L421): 삭제는 스토리지 클러스터가 구성 전이고 SCVM이 정지 상태일 때만 가능하다. 이미 구성된 클러스터나 데이터가 있는 환경은 복구·보존 대상으로 분리한다.

## 엔진 개선 및 검증

최신 요청과 요청자 이력을 기준으로 HCI CCVM·SCVM 재배포 절차 문의를 구분한다. 확인된 4.7.4 절차를 우선 제시하고, 다른 버전이나 재배포 후 장애 진단에는 이 응답을 강제하지 않는다. 실제 초기화 명령을 자동 실행하지 않으며, 운영 배포와 병합은 이번 작업 범위가 아니다.
