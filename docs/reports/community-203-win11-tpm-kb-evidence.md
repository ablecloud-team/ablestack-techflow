# Community #203 Windows 11 TPM 안내 및 KB 근거 보완

[토론 #203](https://community.ablecloud.io/d/203-windows-11-seolci)의 설치 화면은 일반적인 최소 요구 사항 미충족만 표시한다. TPM의 실제 설정값이나 설치 성공 여부는 나타나지 않는다. 질문자는 TPM이 필요한지 물었고 지원 답변 #557은 TPM 활성화를 제안했지만, 해당 조치 후 설치에 성공했다는 공개 후속 결과는 없었다. 선택된 [KB #558](https://community.ablecloud.io/d/203-windows-11-seolci/6)은 이 제안을 TPM 비활성화가 확인된 원인으로 표현했다.

## 근거

- [Microsoft Windows 11 요구 사항](https://learn.microsoft.com/en-us/windows/whats-new/windows-11-requirements): TPM 2.0, 보안 부팅을 지원하는 UEFI, 호환 CPU, 메모리 4GB, 디스크 64GB 등 Windows의 요구 사항을 정의한다. VM에서는 가상 TPM을 사용한다.
- [Mold 4.3.0 생성 UI](https://github.com/ablecloud-team/ablestack-cloud/blob/b58a48992685d16b61f07e66c04b8c0bad4219b9/ui/src/views/compute/DeployVM.vue#L583-L628)와 [TPM 선택지](https://github.com/ablecloud-team/ablestack-cloud/blob/b58a48992685d16b61f07e66c04b8c0bad4219b9/ui/src/views/compute/DeployVM.vue#L1874-L1878): 확장 모드 고급 설정에 TPM이 있고 `V2_0`을 제공한다. 동일 UI 경로·옵션을 4.3.1과 4.3.2 태그에서도 확인했다.
- [KVM 4.3.0 TPM 전달](https://github.com/ablecloud-team/ablestack-cloud/blob/b58a48992685d16b61f07e66c04b8c0bad4219b9/plugins/hypervisors/kvm/src/main/java/com/cloud/hypervisor/kvm/resource/LibvirtComputingResource.java#L2842-L2856): VM 장치 정의에 `tpmversion`을 반영한다.
- [Mold Windows 11 설치 가이드](https://github.com/ablecloud-team/ablestack-docs/blob/50d50ad6c8c548dc58db866ca28b4cbb43cc74d0/docs/userGuide/vms/windows-guide-prepare-vm.md#L183-L211): UEFI·SECURE·TPM 2.0과 100GB 이상 디스크 오퍼링을 안내한다. 이 오퍼링 기준을 Microsoft의 최소 저장 공간 64GB와 구분한다.

## 개선

질문자의 Windows 11·Diplo 4.3 맥락을 유지해 최초 문의와 TPM 후속 질문에 검증된 Mold/KVM 경로를 답한다. 특정 호스트에 실제로 어떤 설정이 적용됐는지나 설치 실패의 개별 원인은 단정하지 않는다. 다른 제품 버전·하이퍼바이저나 별도의 드라이버·디스크 문제는 기존 분석 경로를 유지한다.

KB 작성 시 해결 답변 선택과 조치 결과를 분리한다. 짧은 조치 제안이 선택됐지만 질문자·지원 담당자의 실제 성공 보고가 없는 경우, 생성 결과의 원인 단정을 출력하지 않고 조치를 제안으로 표기한다. 공개 댓글과 선택 상태는 이 코드 변경만으로 수정하지 않는다.
