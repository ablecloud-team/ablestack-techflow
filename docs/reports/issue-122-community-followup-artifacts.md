# Issue #122: Community 후속 첨부 처리 개선

## 재현

2026-09-23 Discussion #186 Post #485는 TXT 1개, PDF 1개(3쪽), PNG 4개를 포함한다. 기존 수집기는 `parser.links[:5]`로 여섯 번째 파일을 제외하고 PDF를 거절했다. 남은 신규 Artifact와 과거 만료 Artifact를 함께 읽으면서 Case 생성이 HTTP 404로 중단됐다. Gateway/Poller 프로세스 Healthy는 답변 성공을 의미하지 않았다.

## 수정

- 원본 첨부 수집과 Community/Comprehensive API, 생성기, 결과의 artifactEvidence 한도를 12개로 통일했다.
- PDF는 Poppler `pdfinfo` 및 `pdftoppm`으로 페이지별 이미지로 변환한다. 20MiB/8쪽, 최대 변 1800픽셀, 페이지 출력 12MiB, 메타데이터 20초/페이지 30초 한도를 둔다. 실패·초과를 warning으로 남긴다. 임시 페이지는 처리 후 제거한다.
- 원본 PDF 한 건과 변환 Artifact 여러 건의 개수 계산을 구분한다.
- 현재 첨부는 실제 존재 여부를 확인하고 모두 필수 근거로 지정한다. 만료된 과거 첨부는 제외하되 이전 분석 요약을 유지하고 재열람 불가 사실을 모델에 전달한다.
- 첨부 6개 이상일 때 결과 출력 예산을 늘려 근거 목록이 잘리지 않도록 했다.
- OpenAPI 39개 작업을 0.16.13/12개 한도로 재생성했다.

## 검증

- 최초 통합시험 129건, 최종 품질 보완 후 관련 시험 177건 통과.
- 실제 260922.pdf: 3페이지 렌더 성공(263449/208350/257994바이트).
- 운영 Post #485: TXT 1개 + PDF 페이지 3개 + PNG 4개 = 8개 모두 HTTP 201 등록.
- 같은 요청에 과거 만료 자료 2개가 기록됨. 신규 자료 분석은 계속 진행됨.
- 최종 배포 이미지: `techflow/ai-gateway:followup186-0.16.13-d0e6788`.
- 백업: `/home/ablecloud/techflow-ai-gateway-backups/followup186-20260923`.
- PR #123. 미병합 PR #119/#121의 기존 운영 변경을 포함하므로 순서대로 병합하거나 중복 diff를 확인해야 한다.

## 사람 검토로 확인한 새 근거

TXT의 findmnt/lsblk/multipath 결과는 `/mnt/glue-gfs → vg_glue-lv_glue → mpatha`를 확인해 준다. 과거 오류 경로 sdm/sdac/sdu는 같은 mpatha에 속한다. 현재 조회의 네 경로 ready/running은 과거 시간 초과를 부정하지 않는다.

PNG 네 장은 9월 17일 vioscsi 129(04:52:28), Kernel-General 12(08:41:17), volmgr 161(08:41:22), NTFS 98(E: 오프라인 Chkdsk 요구, 08:41:33)을 보여 준다. 9월 18일 FC 오류 로그와 날짜를 합치지 않는다. volmgr 161만으로 BugCheck 원인을 확정하지 않는다.

PDF 전 3쪽을 렌더해 읽었다. 복제/flatten, 취소, DR·백업 QoS 일정, 경보와 메모리·볼륨 확장 질문이 별도로 포함돼 있다. 문서의 추측·현장 전달 내용을 제품 지원 사실이나 확정 일정으로 취급하지 않는다.

Diplo 소스 `10973eeb4d284e2d35c1004b2b3f92e8208f0fd1`의 KVMStorageProcessor.flattenSharedMountPointQcow2Volume는 Running 도메인을 요구하고 startFlattenRunningVolume는 virsh blockpull --bandwidth를 사용한다. 이것은 게스트 OS 부팅 완료를 검사한다는 뜻이 아니며 모든 스토리지 유형의 일반 규칙도 아니다. 실제 현장 패치와 다를 수 있으므로 배포 버전 대조가 필요하다.

Microsoft 참고: https://learn.microsoft.com/en-us/troubleshoot/windows-server/backup-and-storage/troubleshoot-data-corruption-and-disk-errors

## 실제 게시와 품질 보완 결과

실제 Post #485 재처리는 74.307초 후 HTTP 201로 완료됐다. 자동 답변 Post #486 생성과 관리자 Chat 알림 1회 성공을 확인했다. 이전과 달리 현재 첨부 8개가 모두 생성기에 전달됐다.

자동 답변을 검토하니 TXT의 장치 연결 관계를 다시 요청하고 파일시스템 복구를 먼저 권하는 문제가 있었다. 짧은 로그도 오류 줄 위주로 선별하면서 정상 상태·장치 연결 구간이 제거되는 것이 확인돼, 예산 절반 이하의 작은 진단 파일은 전체를 비밀정보 마스킹 후 보존하도록 수정했다. Windows NamedTemporaryFile 잠금 때문에 로컬 신규 시험은 실행 실패했으나 Linux 운영 이미지의 관련 시험 177건은 통과했다.

모델 지침에 이미 제공된 topology 재질문 금지, 날짜 분리, 스토리지 안정화·복원 가능 백업 후 쓰기 복구, PDF 별도 문의 구분을 추가했다. 공개 답변의 첨부 관찰 결과가 첫 3개에서 잘리지 않게 했다.

검토한 최종 답변을 기존 Post #486에서 교정하고 DB의 draft/response/Assistant Turn을 함께 갱신했다. 전체 topology를 보존한 새 Artifact `3f8f2a3a-ce27-40e6-bf12-96ffc1f0df53`를 원본 후속 Turn #485에 연결했다. 교정본의 장치 연결 사실, 9월 17일/18일 구분, E: 복구 선행 조건, PDF 운영 질문을 브라우저에서 확인했다. 자동 게시 이후 사람 검토로 교정한 결과이며, 최종 문구 전체가 자동 생성된 것으로 보고하지 않는다.

Gateway/Poller는 Healthy, 재시작 0회이며 보호 서비스 컨테이너 ID 변화는 없다. Discussion #186의 대기 항목은 해소됐다. 전체 Poller에는 다른 Discussion #184의 기존 대기 1건이 남아 있어 전체 대기 0건이라고 보고하지 않는다. VM 장애 자체의 근본 원인 확정·현장 복구 완료는 아직 별도다.
