# Community #210 기능·보안변경 문의 검토

관련 Issue: #158. 대상: [질문](https://community.ablecloud.io/d/210), [기존 AI 답변 교정](https://community.ablecloud.io/d/210/2).

## 결론과 공개 답변

장애가 아니라 설정 변경의 가능 여부를 묻는 세 항목이다. 관련 없는 콘솔 구조와 장애 점검 순서를 제거하고 같은 AI 게시물(594)을 수정했다. 질문자 게시물(593)은 수정하지 않았다. 해결 처리나 KB 생성은 하지 않았다.

| 항목 | 소스에서 확인한 기능 | 확인하지 못한 범위 |
|---|---|---|
| 일반계정 SSH 로그인 후 root 전환 | 일반 관리계정·wheel·pam_wheel 구성이 구현되어 있다. | root 계정 잠금·키 인증 차단 등 임의 보안정책 조합의 무영향 보증은 불가하다. |
| CubeOS·Mold·Wall 비밀번호 정기 변경 | OS 계정과 제품별 로컬 사용자 비밀번호 변경 기능이 있다. Wall 외부 인증은 별도 정책을 따른다. | 고객별 외부 인증·저장된 연동 자격정보·강제 만료 정책은 확인되지 않았다. |
| CubeOS SSH 포트 변경 | 관리 화면과 변경 도구가 있으며 내부 클라이언트·호스트 키 수집·방화벽·SELinux 및 해당 구성의 Glue 연동도 함께 처리한다. | 고객 설치 릴리스에 기능이 포함되는지와 공식 적용 대상·절차는 별도 확인이 필요하다. |

미확인 범위는 ABLECLOUD 기술지원센터에 문의하도록 안내했다. 소스의 기능 구현을 고객 설치 버전의 공식 지원 보증으로 바꾸지 않는다. 실제 환경의 계정·SSH 설정 변경은 수행하지 않았다. 전체 보안조치 스크립트 실행도 권하지 않았다.

## 확인한 고정 소스

- Cockpit 플러그인 Diplo `d0e122f01bbf3710cb926f03e0d1164d6493b4aa`:
  - [일반 관리계정·root 전환](https://github.com/ablecloud-team/ablestack-cockpit-plugin/blob/d0e122f01bbf3710cb926f03e0d1164d6493b4aa/shell/host/security_patch.sh#L295-L330)
  - [root 비밀번호 로그인과 키 인증 구분](https://github.com/ablecloud-team/ablestack-cockpit-plugin/blob/d0e122f01bbf3710cb926f03e0d1164d6493b4aa/shell/host/security_patch.sh#L61-L66)
  - [SSH 포트 동시 반영](https://github.com/ablecloud-team/ablestack-cockpit-plugin/blob/d0e122f01bbf3710cb926f03e0d1164d6493b4aa/shell/host/security_patch.sh#L149-L202)
  - [포트 변경 UI](https://github.com/ablecloud-team/ablestack-cockpit-plugin/blob/d0e122f01bbf3710cb926f03e0d1164d6493b4aa/src/features/main.js#L6425-L6453)
  - [현재·새 포트와 대상 옵션](https://github.com/ablecloud-team/ablestack-cockpit-plugin/blob/d0e122f01bbf3710cb926f03e0d1164d6493b4aa/python/security_patch/security_patch.py#L55-L65)
- Mold Diplo `c2baaf9d507bdffa8dbafeee0c32b19c1c52f843`: [사용자 비밀번호 변경 API](https://github.com/ablecloud-team/ablestack-cloud/blob/c2baaf9d507bdffa8dbafeee0c32b19c1c52f843/api/src/main/java/org/apache/cloudstack/api/command/admin/user/UpdateUserCmd.java#L37-L68)
- Wall `f27b3f1b0b35489e05c64924b5cff7dc64dd2f6d`: [비밀번호 변경 처리](https://github.com/ablecloud-team/ablestack-wall/blob/f27b3f1b0b35489e05c64924b5cff7dc64dd2f6d/pkg/api/user.go#L220-L254), [외부 인증 예외](https://github.com/ablecloud-team/ablestack-wall/blob/f27b3f1b0b35489e05c64924b5cff7dc64dd2f6d/public/app/features/profile/ChangePasswordForm.tsx#L16-L25).

## 원인과 보완

1. 기존 검색은 Mold라는 제품명만으로 콘솔 구현을 확장했다. 보안·계정·포트 지원 문의에는 관련 구현을 우선하고 콘솔 근거를 제외한다. 고정 소스 네 항목을 추가했다.
2. 질문 세 개가 하나의 장애 진단 문서로 변환되었다. `support_intent.py`에서 기능·지원·변경 가능 문의를 분리하고 질문 수와 순서를 보존한다. HTML 목록 번호가 없어진 입력도 처리한다.
3. 필수 Provider JSON 필드를 늘리지 않고 기존 `recommendedActions`에 질문별 판정을 요구한다. 모든 질문과 제품 영역이 포함됐는지 검사한다. 누락·잘못된 형식·진단 명령·장애 자료 요청이 있으면 확인 불가와 지원센터 안내로 안전하게 전환한다. Provider 자체 실패는 여전히 실패·재시도 대상으로 유지한다.
4. 기능 설명은 장애 조치 진전성 대신 항목별 완결성을 검사한다. 일반 장애와 실제 명령 수행 안내는 기존 안전 검사를 유지한다. 단일 장애성 보안 문의를 새 경로로 가로채지 않는 회귀시험도 수행한다.
5. 공개 답변에는 번호별 결론·조건·미확인 범위를 표시한다. 레거시 KB 변환기가 번호형 제목을 없애지 않도록 변환 대상을 기존 KB 제목으로 제한했다.

## 검증과 범위

- 격리한 WSL ext4 체크아웃에서 AI Gateway 전체 단위·API 회귀시험 504개를 통과했다(기존 493개 + 신규 11개). 실제 운영 모델을 변경 코드로 호출한 E2E나 고객 환경의 설정 변경 시험을 의미하지 않는다.
- 추가 시험: 질문 수·순서, HTML 목록 번호 유실, UTF-8 예산, 다중 제품 누락, 관련 소스 선택, 지원센터 이관, Provider 실패 유지, 동일 게시 요청 멱등성, 번호형 제목 보존.
- 공개 게시 직전·직후 사람 댓글과 해결 선택의 서명이 동일함을 확인했다. 답변을 같은 게시물에서 교정하고 Case·Response·Turn을 동기화했다. 중복 댓글은 생성하지 않았다.
- 이번 PR은 코드 검토 요청이다. 기존 PR #157과 별도로 최신 local main에서 작성했으며 자동 병합·운영 배포·서비스 설정 변경은 하지 않는다. API 경로·필수 Provider JSON 필드·DB 스키마·이미지 버전은 변경하지 않는다. 후속 통합 배포 시 릴리스 버전을 결정한다.

## 롤백

코드는 이 PR을 되돌린다. 공개 답변 교정은 배포와 독립적인 운영자 검토 결과이며 코드 롤백으로 과거의 부적절한 답변을 복원하지 않는다. 추가 교정 시 최신 공개 근거와 AI 소유권을 재검증하고 게시물 594를 같은 위치에서 수정한다.
