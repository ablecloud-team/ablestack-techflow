# Issue #71 Flarum 1.8.18 업데이트 및 운영 반영 보고서

## 결론

PR #75를 병합한 뒤 승인된 운영 작업을 수행했다. ABLESTACK Community는 현재 **Flarum 1.8.18, Flarum Nicknames 1.8.3, Debug Off, SMTP 유지** 상태이며 외부 첫 화면은 HTTP 200이다.

첫 실행은 운영 서버가 자신의 공개 URL로 접속할 수 없는 NAT loopback 제약 때문에 배포 후 점검이 시간 초과됐다. 배포 스크립트가 즉시 1.8.10 기준선으로 자동 복원했고 데이터 차이는 없었다. 점검을 `127.0.0.1`과 실제 Host/HTTPS 전달 헤더를 사용하는 방식으로 보정한 두 번째 실행은 정상 완료됐다.

사용자 39명, 토론 120건, 게시물 320건, 첨부 115개와 첨부 전체 SHA-256은 업데이트 전후 정확히 일치한다. 브라우저 Community 화면, TechFlow Community poller, AI Gateway, Activepieces가 정상이며 보호 대상 GitHub→Chat 웹훅은 변경하지 않았고 보호 가드도 통과했다.

## 변경 및 검증 범위

- Flarum Core 1.8.10 → 1.8.18
- Flarum Nicknames 1.8.2 → 1.8.3
- 앱·설정·DB·업로드 동일 변경 ID 백업
- Composer 의존성, Migration, 캐시와 한글 Asset 재생성
- DB, 게시물, 첨부 정합성 확인
- Community 브라우저 기능과 TechFlow 통합 회귀
- 실패 시 자동 롤백 및 재실행 절차 검증

대용량 로그/압축 업로드는 Issue #72, UI 현대화는 Issue #73, 백업·모니터링·잔여 보안 항목은 Issue #74에서 이어간다. PR #65는 이 작업과 분리해 유지한다.

## 운영 기준선과 최종 상태

| 구분 | 변경 전 | 변경 후 |
|---|---|---|
| Flarum Core | 1.8.10 | 1.8.18 |
| Flarum Nicknames | 1.8.2 | 1.8.3 |
| Symfony Mailer | 6.1.11 | 6.1.11 |
| Mail driver | SMTP | SMTP |
| Debug | Off | Off |
| Nginx / PHP-FPM / MariaDB | active | active |
| 외부 URL | HTTP 200 | HTTP 200 |

운영 서버 루트 파일시스템은 약 1TB이며 약 956GB가 남아 있다.

## 운영 실행 기록

### 첫 번째 실행: 자동 롤백 성공

- 변경 ID: `issue-71-20260814T132041Z`
- 결과: `AUTO_ROLLBACK_PASS`
- 원인: 서버 내부에서 공개 URL을 확인하는 요청이 NAT loopback 미지원으로 시간 초과
- 복원 결과: Core 1.8.10, Nicknames 1.8.2, 사용자/토론/게시물/첨부 기준선 복구
- `rollback.diff`: 비어 있음
- 판단: 제품 오류나 데이터 손상이 아니라 점검 경로 문제이며 자동 보상 절차가 정상 작동함

### 두 번째 실행: 운영 업데이트 성공

- 변경 ID: `issue-71-20260814T132424Z`
- 백업 경로: `/var/backups/techflow-flarum/issue-71-20260814T132424Z`
- 보정한 점검: `127.0.0.1`에 `Host: community.ablecloud.io`, `X-Forwarded-Proto: https` 헤더를 사용
- 앱 백업: 237,062,765 bytes
- 압축 DB 백업: 167,262 bytes, SHA-256 검증 PASS
- 결과: `UPGRADE_SUCCESS`

첫 실행의 백업 `/var/backups/techflow-flarum/issue-71-20260814T132041Z`도 롤백 증적으로 보존한다.

## 데이터 정합성

| 지표 | 업데이트 전 | 업데이트 후 | 결과 |
|---|---:|---:|---|
| 사용자 | 39 | 39 | 일치 |
| 토론 | 120 | 120 | 일치 |
| 게시물 | 320 | 320 | 일치 |
| 첨부파일 | 115 | 115 | 일치 |
| 첨부 용량 | 26,060,120 bytes | 26,060,120 bytes | 일치 |
| 첨부 SHA-256 | `35cbac9f...ff50` | `35cbac9f...ff50` | 일치 |

## Community와 TechFlow 검증

- Community 첫 화면과 실제 토론 상세 화면 로딩 통과
- 한국어 화면에 내부 번역 키 노출 0건
- 브라우저 콘솔 오류·경고 0건
- 외부 Admin 경로 HTTP 403은 기존 접근 정책이며 Flarum 장애가 아님
- Flarum CLI로 Core 1.8.18과 확장 로딩 상태 확인
- 유지보수 시간에 일시 실패했던 Community poller가 자동 회복
- 회복 후 반복 poll 결과 `failed=0`, `seenPosts=146`
- AI Gateway, Activepieces 및 관련 DB/Redis 컨테이너 healthy
- GitHub→Chat 보호 서비스 가드: `state=frozen`, `guard=passed`

## 보안 검토

`flarum/nicknames`의 CVE-2026-30913은 1.8.3 업데이트로 제거됐다.

`symfony/mailer` 6.1.11에는 Sendmail 인자 주입 취약점 CVE-2026-45068이 남는다. Flarum 1.8 의존성 제약으로 Mailer 6.4를 함께 설치할 수 없으며, 운영은 영향 경로가 아닌 SMTP를 계속 사용한다. Sendmail로 전환하지 않고 장기 교체는 Issue #74에서 추적한다.

## 최종 판정

- PR #75: 병합 완료
- 운영 Community: Flarum 1.8.18 / Nicknames 1.8.3
- 운영 데이터 및 첨부: 정합성 PASS
- Community 브라우저 검증: PASS
- TechFlow 통합: PASS
- GitHub→Chat 보호 서비스: 변경 없음, 가드 PASS
- 판정: **Go 완료**

## 후속 작업

1. Issue #72 대용량 로그·압축 업로드 환경 개선
2. Issue #73 Community UI 현대화
3. Issue #74 백업·모니터링·잔여 보안 항목 강화

상세 절차는 `docs/runbooks/flarum-1.8.18-upgrade-rollback.md`, 구조화 증적은 `docs/evidence/issue-71/flarum-1.8.18-validation.json`과 `docs/evidence/issue-71/flarum-1.8.18-production-rollout.json`에 있다.
