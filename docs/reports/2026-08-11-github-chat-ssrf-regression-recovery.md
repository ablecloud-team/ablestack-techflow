# GitHub→Synology Chat SSRF 회귀 장애 복구 보고서

> 복구일: 2026-08-11
>
> 대상: Issue #19 `github-chat-v1`

## 1. 결론

GitHub 조직 Webhook과 Event Gateway는 정상 접수했지만 Activepieces Worker가 내부 Chat Adapter `172.30.19.10`을 SSRF 정책으로 차단해 Chat 메시지가 게시되지 않았다. 시험 서버의 `AP_SSRF_ALLOW_LIST`에 `172.30.19.10/32`를 복구하고 App·Worker만 재생성한 뒤 실제 Push 테스트가 `SUCCEEDED`이고 Chat 응답이 `success=true`인 것을 확인했다.

## 2. 원인과 영향

- 조직 Hook `650151350`은 활성 상태였고 최신 Push·PR Merge Delivery는 HTTP `202`였다.
- Event Gateway 0.4.0은 두 이벤트를 `github_webhook_accepted`로 기록했다.
- Activepieces `github-chat-v1`은 2026-08-10 03:25 UTC까지 성공했고 06:19 UTC 이후 실패했다.
- Issue #45 RAG 배포 기본값이 SSRF 허용 목록을 AI Gateway `.3`과 Control Plane `.9`만 남기면서 기존 Chat Adapter `.10`을 누락했다.
- 최신 실패 Run은 모두 `SSRFBlockedError`였으며 Synology Chat에는 요청이 도달하지 않았다.

## 3. 복구

1. PostgreSQL·Redis·Activepieces 상태 백업을 `github-chat-ssrf-recovery` Label로 생성했다.
2. 서버 `.env`의 허용 목록을 `.3/32`, `.9/32`, `.10/32`로 복구했다.
3. App과 Worker만 `--no-deps --no-build --force-recreate`로 재생성했다.
4. PostgreSQL·Redis·Ingress·Event Gateway는 재생성하지 않았다.
5. 모든 서비스 Health와 Worker Polling `ready`를 확인했다.

## 4. 실증 결과

| 검증 | 결과 |
|---|---|
| 서명 Ping | HTTP 200 |
| 위조 서명 | HTTP 401 |
| 비병합 PR | HTTP 200, Chat 미호출 |
| 외부 Activepieces 직접 Webhook | HTTP 404 |
| 테스트 Push | Gateway HTTP 202 |
| 동일 Delivery 재전송 | HTTP 200, 중복 게시 없음 |
| Activepieces Run | `KGXMd3sef0ijk9cpehQm4`, `SUCCEEDED` |
| Chat Adapter | `chat_delivery_succeeded` |

실제 Secret, Payload, Chat Token과 인증 응답은 기록하지 않았다.

## 5. 재발 방지와 동결 정책

- `github-chat-v1`을 `FROZEN` 보호 서비스로 등록했다.
- Flow Manifest Checksum, Flow ID, Published Version, 내부 Adapter 주소, 고정 IPv4와 Ingress를 배포 전 검사한다.
- RAG 배포도 `.10/32`를 제거할 수 없으며 보호 검사 실패 시 컨테이너 변경 전에 중단한다.
- 해당 서비스의 계약 변경은 제품 책임자의 명시적 승인 없이는 수행하지 않는다.
