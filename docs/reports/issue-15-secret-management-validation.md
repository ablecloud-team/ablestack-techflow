# Issue #15 비밀정보 관리 완료 보고서

## 1. 결론

TechFlow 단일 서버 실증의 Secret 저장·주입·교체·폐기 방식을 ADR-0002로 확정하고 실제 테스트 서버에 구현했다.

기존 배포 경로의 `.env 0600`은 `/etc/ablestack-techflow/secrets/activepieces.env`로 마이그레이션되었다. 보호된 파일은 `root:ablecloud 0640`, 상위 디렉터리는 `0750`이며 배포 경로에는 심볼릭 링크만 남는다.

Webhook Secret은 현재·직전 두 상태의 Grace Period를 지원한다. 실제 외부 HTTPS 경로에서 현재 값 `202`, 직전 값 `202`, 폐기 후 현재 값 `202`, 폐기된 직전 값 `401`을 확인했다.

## 2. 구현 결과

| 영역 | 결과 |
|---|---|
| 저장 | 배포 자산과 분리된 `/etc` 보호 파일 |
| 주입 | Compose `env_file`과 `.env` 링크 |
| 접근 | `root:ablecloud 0640`, 디렉터리 `0750` |
| 갱신 | Python 원자적 교체, Secret 값 명령행 미사용 |
| Webhook 교체 | 현재·직전 Grace Period, 폐기·롤백 |
| 영향 제한 | Event Gateway만 재생성, Redis 유지 |
| 감사 | 값 없는 JSONL 변경 기록 |
| 노출 검사 | 배포 파일·컨테이너 로그 0건 |
| 복구 | 서비스 재시작·호스트 재부팅 후 재검증 |

## 3. 자산

| 자산 | 역할 |
|---|---|
| `ADR-0002` | Secret 소유권, 저장, 분류와 수명주기 결정 |
| `secretctl.sh` | Bootstrap, 교체, 폐기, 롤백과 통합 검증 |
| `secret_env.py` | 권한·소유권을 보존하는 원자적 환경 파일 갱신 |
| `secret_scan.py` | 실제 Secret 값의 저장소·로그 노출 검사 |
| `verify-secrets.sh` | 권한·Inventory·노출 통합 검증 |
| Event Gateway | 현재·직전 HMAC Secret 검증 |
| Secret Runbook | 유형별 교체·백업·사고 대응 절차 |
| 구조화 JSON | 환경·정책·검증의 단일 증적 |

## 4. 검증 결과

| ID | 검증 | 결과 |
|---|---|---|
| V1 | 기존 `.env`의 보호 저장소 마이그레이션 | PASS |
| V2 | 저장소·디렉터리·감사 파일 권한 | PASS |
| V3 | 필수 Secret 6종 존재, 직전 Secret 비어 있음 | PASS |
| V4 | Gateway 단위 테스트 | 6/6 PASS |
| V5 | 신규 현재 Secret, Grace Period | `202` PASS |
| V6 | 직전 Secret, Grace Period | `202` PASS |
| V7 | 신규 현재 Secret, 폐기 후 | `202` PASS |
| V8 | 폐기된 직전 Secret | `401` PASS |
| V9 | Gateway-only 재생성과 Redis 유지 | PASS |
| V10 | 배포 자산의 실제 Secret 값 노출 | 0건 |
| V11 | 컨테이너 로그의 실제 Secret 값 노출 | 0건 |
| V12 | HTTPS·서명 Webhook 회귀 검증 | PASS |
| V13 | 서비스 재시작 복구 | PASS |
| V14 | 호스트 재부팅 복구 | PASS |
| V15 | 신규 일반 백업의 `.env` 제외 | PASS |

## 5. 감사

`store.bootstrap`, `rotate.prepare`, `rotate.revoke_previous`, `rotate.lifecycle_test` 이벤트가 기록되었다. 기록에는 UTC 시각, 운영자, 동작, 논리 대상과 성공 여부만 존재하며 실제 Secret, 서명과 요청 Body는 없다.

## 6. 백업 판정

Issue #14의 `.env` 포함 Archive 한 개는 root 전용 디렉터리 `0700`, Archive `0600`으로 격리했다. Issue #16의 복구 검증 완료 후 해당 구형 Archive만 안전 삭제했고, Issue #15에서 생성한 값이 없는 사전 배포 Archive는 보존했다.

Secret 복구본의 상태 Archive 분리, OpenPGP AES-256 암호화와 실제 격리 복원 훈련은 Issue #16에서 완료했다. 고객 배포에서는 암호화 Bundle과 Passphrase를 서로 다른 승인된 외부 장애 영역에 보관해야 한다.

## 7. 보안 영향

- Secret 원문은 Git, Issue, Flow JSON, 보고서와 일반 로그에 기록하지 않는다.
- HMAC 도구는 Secret을 명령행 인자로 전달하지 않는다.
- 직전 Webhook Secret이 존재하면 다음 교체를 거부한다.
- 유출이 의심된 값은 Grace Period 없이 즉시 폐기한다.
- `AP_ENCRYPTION_KEY`는 Connection 복호화 Root이므로 임의 교체하지 않는다.
- 단일 서버 파일 저장소는 실증 기준이며 고객 제품은 Secret Provider와 고객별 분리가 필요하다.
- 고객 공개 여부는 제품 책임자의 별도 결정이며 구현 완료 기준에 포함하지 않는다.

## 8. 완료 판정

Issue #15의 완료 기준인 Git·Issue·로그 비노출 운영 기준, 런타임 주입, 접근 권한, 교체·폐기, 감사와 사고 대응을 ADR·코드·Runbook으로 확정했다. 실제 서버에서 대표 Secret 수명주기와 재부팅 복구까지 통과했으므로 Issue #15를 완료로 판정한다.

후속 Issue #16에서 PostgreSQL·Redis 백업, 격리 복구 훈련과 Secret Escrow 복구 검증을 완료했다.
