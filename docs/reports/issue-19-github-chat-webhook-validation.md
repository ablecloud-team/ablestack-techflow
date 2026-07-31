# Issue #19 GitHub 조직 Webhook·Synology Chat 자동화 완료 보고서

> 상태: **완료**
>
> 검증일: 2026-07-31
>
> 관련 이슈: [#19](https://github.com/ablecloud-team/ablestack-techflow/issues/19)
>
> 구현 PR: [#35](https://github.com/ablecloud-team/ablestack-techflow/pull/35)

## 1. 완료 결론

기존 `chat.ablecloud.io` 직접 조직 Webhook을 TechFlow Endpoint로 전환했다. GitHub Push와 PR Merge는 Event Gateway에서 서명 검증·정규화·중복 억제를 거친 뒤 Activepieces Flow가 실행하고, 내부 Chat Adapter가 Synology 응답 본문의 `success=true`까지 확인한다.

최종 조직 Hook 카나리 PR #38에서 PR Merge와 Merge Commit Push가 같은 시각에 도착했으며 다음 결과를 확인했다.

| 계층 | PR Merge | Push |
|---|---:|---:|
| GitHub Delivery | 202 | 202 |
| Activepieces | `SUCCEEDED` | `SUCCEEDED` |
| Synology Chat | `success=true` | `success=true` |

정상 동작 중인 KakaoWork 조직 Hook은 URL Host, `push` 이벤트와 SSL 설정을 변경하지 않았다.

## 2. 구현 자산

| 자산 | 구현 내용 |
|---|---|
| Event Gateway `0.2.0` | GitHub HMAC, 조직·이벤트 allowlist, 최소 Payload, 7일 중복 방지, Chat 응답 판정 |
| Activepieces Flow | `github-chat-v1`, Catch Webhook → 내부 Chat Adapter |
| Caddy | `/techflow/hooks/github/chat`만 Gateway로 전달, `/api/v1/webhooks/*` 외부 404 |
| 격리 네트워크 | `automation_egress`의 제어 API `.9`, Chat Adapter `.10`만 SSRF 허용 |
| Chat 전송 슬롯 | Redis 직렬화, 최소 600 ms 간격 |
| 릴리스 잠금 | Gateway Image ID `sha256:dc8183f0…6a8ec` 고정 |
| 검증 스크립트 | `verify-github-chat.py` |
| 운영 문서 | 설계·구조화 계약·Flow Manifest·Runbook·본 보고서 |

실제 Secret과 인증정보는 저장소·Issue·PR·보고서에 포함하지 않았다.

## 3. Activepieces 실행 기준

| 항목 | 값 |
|---|---|
| 제품 버전 | Activepieces Community Edition `0.86.3` |
| Flow 이름 | `TechFlow - GitHub to Synology Chat v1` |
| Flow ID | `BjLSSjbSp3tyNLjnxWUS8` |
| 최종 Published Version | `pRg5UyXXPlVUwdutbrNMz` |
| Trigger | `@activepieces/piece-webhook` `0.1.39` |
| Action | `@activepieces/piece-http` `0.11.14` |
| 상태 | `ENABLED`, `LOCKED` |

Community Edition의 사설 Piece 배포에 의존하지 않도록 Chat Token과 프로토콜 판정은 서버의 내부 Adapter가 소유한다. Activepieces는 시각적 실행과 Run 이력을 담당하며, 향후 자체 Piece 제공 여부는 제품화 단계에서 별도로 결정할 수 있다.

## 4. 배포 결과

### 4.1 변경 전 보호

- `issue19-predeploy`, `issue19-ssrf-allowlist`, `issue19-worker-control-network`, `issue19-chat-pacing` Label로 상태 백업을 생성했다.
- 배포 전 Source Lock과 배포 후 Runtime Lock을 보관했다.
- PostgreSQL·Redis·Activepieces Cache Volume을 보존했다.

### 4.2 최소 변경 배포

1. Gateway 0.2.0을 서버에서 재현 빌드했다.
2. 빌드 Image ID를 `image-lock.json`에 고정했다.
3. Gateway·Ingress 변경을 우선 적용했다.
4. SSRF 제약 발견 후 전용 네트워크를 추가하고 app/worker만 재생성했다.
5. Chat 전송 슬롯 추가 후 Gateway만 재생성했다.
6. 최종 6개 서비스 Health와 실행 이미지 잠금을 검증했다.

최종 Health는 Ingress, Event Gateway, App, Worker, PostgreSQL, Redis 모두 `healthy`, Worker Polling은 `ready`였다.

## 5. 계약·보안 검증

| ID | 검증 | 결과 |
|---|---|---|
| T01 | 유효 GitHub Ping | 200 |
| T02 | 위조 HMAC | 401 |
| T03 | 신규 Push 접수 | 202 |
| T04 | 동일 Delivery 재수신 | 200, 추가 Chat 없음 |
| T05 | 비병합 PR Close | 200, Chat 미호출 |
| T06 | 외부 Activepieces 직접 Webhook | 404 |
| T07 | 다른 조직 Payload | 계약 테스트에서 거부 |
| T08 | HTTP 200·`success=false` | 단위 테스트에서 `FAILED` 판정 |
| T09 | Secret 검사 | 저장소 배포 자산 49개, 노출 0건 |
| T10 | 자동 테스트 | 25건 통과 |

Gateway는 원문 GitHub Payload, HMAC 서명, PR 제목과 Token을 구조화 로그에 기록하지 않는다. Chat Adapter 로그도 Event ID와 허용된 오류 코드만 남긴다.

## 6. 실제 GitHub E2E 근거

### 6.1 카나리 PR

| PR | 목적 | 결과 |
|---:|---|---|
| #36 | 저장소 Hook 기본 Push·PR Merge | PR 성공, Push는 기존 직접 Hook과 충돌해 411 발견 |
| #37 | 600 ms 전송 슬롯 | 임시 Hook과 기존 조직 Hook의 이중 전송 영향 재확인 |
| #38 | 임시 Hook 제거 후 조직 Hook 단독 최종 검증 | PR Merge·Push 모두 성공 |

초기 실패를 숨기지 않고 Synology 공식 운영 지침의 최소 0.5초 간격과 실제 `411(create post too fast)`를 반영해 Redis 전송 슬롯을 추가했다. 최종 전환 전에 임시 저장소 Hook을 제거해 동일 Push의 이중 전송 원인도 제거했다.

### 6.2 최종 조직 Hook Delivery

| 이벤트 | GitHub Delivery ID | HTTP | Gateway Event ID | 최종 결과 |
|---|---:|---:|---|---|
| PR `closed`, `merged=true` | `3834349419159896064` | 202 | `0ad70430-…-83c8-5ba83947934b` | Chat 성공 |
| Push `refs/heads/main` | `3834349419193434112` | 202 | `0b2417de-…-90e0-f6335e34380e` | Chat 성공 |

두 Activepieces Run은 모두 `SUCCEEDED`였고 Gateway는 `chat_delivery_succeeded` 2건을 기록했다.

### 6.3 다른 조직 Hook 보존

| Hook ID | Host | 이벤트 | Active | 최근 Push |
|---:|---|---|---:|---|
| `293533999` | `kakaowork.com` | `push` | true | HTTP 200 |
| `650151350` | `techflow.ablecloud.io` | `push`, `pull_request` | true | HTTP 202 |

## 7. 런타임 제약과 해결

### 7.1 Activepieces SSRF 보호

`AP_NETWORK_MODE=STRICT`가 Docker 사설 주소를 차단해 초기 Flow가 내부 Adapter와 Activepieces 제어 API에 접근하지 못했다. 사설망 전체를 허용하지 않고 `automation_egress` `/28` 네트워크를 추가해 고정 주소 2개만 허용했다.

### 7.2 Schema 22 표현식

`{{trigger.body...}}`는 API로 생성한 Flow에서 빈 값으로 평가됐다. 최종 Flow는 `{{trigger['output']['body']...}}` 형태로 고정했고, 빈 `url/text/eventId` 실패가 해소됐다.

### 7.3 Synology 성공 판정과 속도 제한

HTTP 200만 보지 않고 JSON `success=true`를 검사한다. `success=false`와 코드 411은 Flow를 실패시킨다. 전송은 Redis Slot으로 직렬화하고 응답 후 600 ms가 지나야 다음 메시지를 허용한다.

## 8. 실패 가시성

의도된 계약 실패와 초기 카나리 실패는 Activepieces Flow Run의 실패 Step에서 확인됐다. TechFlow Observer는 최근 15분 실패를 `flow_failures_warning`으로 집계했으며 Payload와 Secret을 복제하지 않았다. 실패가 15분 창에서 벗어나면 경보가 자동 해제되는 기존 ADR-0004 정책을 유지한다.

담당자·외부 실패 알림 채널은 아직 미정이므로 추가 통보는 구현하지 않았다. 현재 운영 확인 지점은 Activepieces Flow Runs와 Observer 파일이다.

## 9. 롤백 준비

롤백 첫 단계는 조직 Hook `650151350` 비활성화, 두 번째는 `github-chat-v1` Flow 비활성화다. 서비스 롤백은 `runtime-lock.previous.json`과 `rollback-release.sh`를 사용한다. 기존 직접 Chat Hook은 업무 실패 상태였으므로 복원보다 비활성 유지가 기본이며, 필요 시 서버 보호 Secret의 Chat URL로 이전 설정을 복구할 수 있다.

Volume과 Flow Run 이력은 롤백 시에도 삭제하지 않는다. 정상 KakaoWork Hook은 롤백 범위가 아니다.

## 10. 완료 판정

- [x] Push 메시지 정상 게시
- [x] PR Merge 메시지 정상 게시
- [x] 비병합 PR 무시
- [x] GitHub HMAC 검증
- [x] Delivery ID 중복 억제
- [x] HTTP 200·업무 실패 분리
- [x] Activepieces·Observer 실패 가시성
- [x] 기존 정상 조직 Hook 보존
- [x] 서버 배포·검증·롤백 절차 자산화
- [x] 저장소 Secret 노출 0건

Issue #19의 구현·배포·조직 Hook 전환·E2E 검증 범위는 완료했다.
