# Community #209 운영 문의 전환 검토

관련 Issue: #162. 사례: [HCI 종료·기동 답변](https://community.ablecloud.io/d/209/10), [웹 부하분산·CubeOS 업데이트 답변](https://community.ablecloud.io/d/209/12). 기준 코드: main `9225c7d`.

## 공개 처리

- 질문자는 이전 CCVM 배포 문제의 해결을 보고한 뒤 HCI 종료·기동, 웹 트래픽 부하분산과 CubeOS 업데이트를 문의했다. 기존 장애와 새 운영 주제를 구분했다.
- AI 게시물600·602를 같은 위치에서 교정했다. 공식 HCI 절차·자동 종료의 사전조건, Mold의 트래픽 LB와 별도 Nginx 게스트 구성, ISO 기반 업데이트와 무인 정기 업데이트의 차이를 안내했다.
- ‘관련 기능/절차를 확인하지 못했다’는 기존 설명을 교정했다. 고객 설치 버전에 기능이 포함되는지와 구성별 공식 적용 범위까지 보증하지는 않는다.
- 현재 질문599·601에는 첨부가 없다. 엔진 Turn·Artifact 등록 정보를 대조했으며 이전 배포 이미지나 로그를 현재 운영 문의의 근거로 재분석했다고 주장하지 않았다.
- 게시 직전·직후 공개 사람 댓글·해결 선택 서명을 확인하고 AI 소유권과 버전5·6을 대조했다. 현재 Case·Response·Turn과 과거 Response·Turn을 동기화하고 교정 감사 이벤트를 남겼다. 사람 댓글, 해결 선택은 변경하지 않았다.
- 이전 배포의 해결 보고를 전체 토론의 최종 해결로 처리하지 않았다. 새 운영 질문이 이어지고 해결 답변이 선택되지 않아 `WAITING_RESOLUTION`을 유지하며 KB를 임의 생성하지 않았다.
- [Community #213](https://community.ablecloud.io/d/213)은 관리자 게시물605에서 파트너 공지·기술지원센터 문의를 안내했다. 별도 AI 댓글을 추가하거나 기존 관리자 안내를 수정하지 않았다. 특정 CVE의 유효성·영향 버전을 검증 완료했다고 주장하지 않는다.

## 원인과 최소 수정

1. 원래 제목·인용한 이전 답변의 배포/마이그레이션 키워드가 현재 웹 트래픽 문의를 오염시켰다. 최신 질문의 명시적 의미 정정 뒤를 기준으로 운영 주제를 분류하고 관련 문서·소스의 검색어를 우선한다.
2. HCI 전체 재기동 문서, Mold 트래픽 LB 문서/API, Cube ISO 업데이트 구현이 검색 근거에 누락됐다. 검토한 고정 근거 네 항목을 추가했다. 미검색을 미지원의 증거로 바꾸지 않는다.
3. 비장애 운영·기능·취약 버전 적용 범위 문의가 장애 조치·시각·로그 요청 형식으로 표시됐다. 설명 의도를 전달하고 근거 부족 시 기술지원센터 안내를 사용한다. 실제 장애와 Provider 실패 경로는 유지한다.
4. 금지한 인라인 명령이 복사 가능한 실행 블록으로 바뀌었다. 금지·실행하지 말라는 문장은 그대로 보존한다.

## 검토한 고정 근거

- Docs `f25e3d652cfcc14e5b794781ead65e54d8de8bfb`: `docs/administration/system-restart-hci.md`, `docs/admin-guide/cube/cube-admin-guide-ablestack-hci.md`, `docs/administration/mold/network&traffic-mngt-guide.md` 703-737행, `docs/userGuide/3tiers/windows/windows-guide-web.md`.
- Cockpit Diplo `d0e122f01bbf3710cb926f03e0d1164d6493b4aa`: `python/host/ablestack_update.py` 44-69·389-426행, `src/features/main.js` 5422·5460·5629행, `docs/update-workflow.md`.
- Cloud Diplo `c2baaf9d507bdffa8dbafeee0c32b19c1c52f843`: `api/src/main/java/org/apache/cloudstack/api/command/user/loadbalancer/CreateLoadBalancerRuleCmd.java` 52-93행.
- Nginx 공식 [HTTP 부하분산](https://nginx.org/en/docs/http/load_balancing.html), [upstream](https://nginx.org/en/docs/http/ngx_http_upstream_module.html), [설정·기동 가이드](https://nginx.org/en/docs/beginners_guide.html).
- 공개 문서의 `latest/administration/system-restart-hci/`, `latest/administration/mold/network%26traffic-mngt-guide/` HTTP200 확인. 현재 문서의 존재와 고객 설치 릴리스의 포함 여부는 별개다.

## 시험·제한·운영 인계

- 격리 WSL ext4/Python3.12에서 전체524개 회귀시험 통과(기존515 + 신규9).
- 현재 정정 질문과 이전 CCVM 제목/인용문 경계, 실제 장애·KB 경계, 관련 소스 선택, 비장애 근거 부족 안내, 명령 금지 표현 보존, 자동 게시·중복 방지를 검증했다.
- OpenAPI39 operations와 기존 필수 필드·DB 스키마 유지. 후보 코드의 실제 운영 모델 E2E나 고객 HCI 종료·Nginx·업데이트 실행 시험을 의미하지 않는다.
- 이번 예약 작업은 개선 PR 등록까지만 수행한다. 운영 엔진은0.16.33이며 코드 병합·배포·서비스/권한/네트워크 설정 변경은 하지 않는다. 공개 답변은 기존 운영 메서드로 교정한 검토 결과이지 후보 코드가 운영 중이라는 뜻이 아니다.
- 코드 롤백은 PR 변경을 되돌린다. 공개 답변을 과거의 부정확한 내용으로 자동 복원하지 않는다. 추가 교정은 새 공개 입력을 다시 검토하고 동일 게시물에서 수행한다.
