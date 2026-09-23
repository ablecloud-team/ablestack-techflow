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

- conversation/community/poller/responses 129건 통과.
- 실제 260922.pdf: 3페이지 렌더 성공(263449/208350/257994바이트).
- 운영 Post #485: TXT 1개 + PDF 페이지 3개 + PNG 4개 = 8개 모두 HTTP 201 등록.
- 같은 요청에 과거 만료 자료 2개가 기록됨. 신규 자료 분석은 계속 진행됨.
- 배포 이미지: `techflow/ai-gateway:followup186-0.16.13-e4fd1e4`.
- 백업: `/home/ablecloud/techflow-ai-gateway-backups/followup186-20260923`.
- PR #123. 미병합 PR #119/#121의 기존 운영 변경을 포함하므로 순서대로 병합하거나 중복 diff를 확인해야 한다.

## 사람 검토로 확인한 새 근거

TXT의 findmnt/lsblk/multipath 결과는 `/mnt/glue-gfs → vg_glue-lv_glue → mpatha`를 확인해 준다. 과거 오류 경로 sdm/sdac/sdu는 같은 mpatha에 속한다. 현재 조회의 네 경로 ready/running은 과거 시간 초과를 부정하지 않는다.

PNG 네 장은 9월 17일 vioscsi 129(04:52:28), Kernel-General 12(08:41:17), volmgr 161(08:41:22), NTFS 98(E: 오프라인 Chkdsk 요구, 08:41:33)을 보여 준다. 9월 18일 FC 오류 로그와 날짜를 합치지 않는다. volmgr 161만으로 BugCheck 원인을 확정하지 않는다.

PDF 전 3쪽을 렌더해 읽었다. 복제/flatten, 취소, DR·백업 QoS 일정, 경보와 메모리·볼륨 확장 질문이 별도로 포함돼 있다. 문서의 추측·현장 전달 내용을 제품 지원 사실이나 확정 일정으로 취급하지 않는다.

Diplo 소스 `10973eeb4d284e2d35c1004b2b3f92e8208f0fd1`의 KVMStorageProcessor.flattenSharedMountPointQcow2Volume는 Running 도메인을 요구하고 startFlattenRunningVolume는 virsh blockpull --bandwidth를 사용한다. 이것은 게스트 OS 부팅 완료를 검사한다는 뜻이 아니며 모든 스토리지 유형의 일반 규칙도 아니다. 실제 현장 패치와 다를 수 있으므로 배포 버전 대조가 필요하다.

Microsoft 참고: https://learn.microsoft.com/en-us/troubleshoot/windows-server/backup-and-storage/troubleshoot-data-corruption-and-disk-errors
