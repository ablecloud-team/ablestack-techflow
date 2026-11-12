# 해결 이후 후속 답변에 따른 KB 갱신 검증

관련 Issue: #146. Gateway 변경 버전: 0.16.29. 작업일: 2026-11-11 KST.

## 결과

- #199의 KB550 이후 사람의 실제 성공 보고559가 올라오는 흐름을 로컬 API 시험으로 재현했다. 새 KB 게시 없이 같은550을 수정하고 원래 해결 출처548은 보존한다. 보고자는 질문자가 아닌 참여자라는 지침을 종합 입력에 고정한다.
- 질문자·권한 확인된 관리자가 새로운 해결 답변을 선택하는 경로도 기존 KB를 재사용한다. 이때만 해결 선택 출처를 새 선택으로 바꾼다.
- 실패 중에는 진행 중 메타데이터를 유지하고 Poller 완료 확인을 거부한다. 게시 성공 후 선택 실패는 게시를 반복하지 않고 선택만 재시도한다. 숨김·삭제·미해결 내용으로의 변경은 해당 대기를 취소한다.
- 원문·작성자·현재 해결 선택을 공개 수정 직전에 대조한다. AI 원본·질문·제안·인용·미해결 보고는 후속 성공으로 취급하지 않는다. 같은 worker의 중복 동시 전달과 역순 입력도 시험한다.
- PostgreSQL JSON 메타데이터 및 SQL 인자 계약을 모의 연결로 확인했다. DB 스키마 추가는 없으며 실 PostgreSQL/실모델 통합 검증은 이번 로컬 시험 범위가 아니다.

## 자동 시험

`services/ai-gateway`에서 아래 11개 모듈을 실행하여 **309개 회귀시험 통과**:

```text
python -m unittest tests.test_community tests.test_conversation tests.test_versioned_assist tests.test_community_poller tests.test_store tests.test_postgres_store tests.test_chat_assist tests.test_epic4_operations tests.test_responses tests.test_community_kb_refresh tests.test_community_review_candidates
```

추가로 `python -m unittest discover -s tests`를 실행했다. 해당 시점 전체455개 중453개 통과, 아래 기존 로컬 환경 문제2건이 남았다. 관련 기존 테스트·로그 파서는 이 PR에서 수정하지 않았다.

| 시험 | 결과 및 원인 |
|---|---|
| `test_container_contract.test_shell_scripts_are_forced_to_lf` | ignored `tmp/research/activepieces-0.86.3` 아래24개 외부 연구용 셸 파일의 CRLF를 저장소 전체 재귀 검사가 포함함 |
| `test_log_evidence_completeness.test_small_diagnostic_keeps_topology_between_errors_and_masks_secrets` | Windows에서 열린 NamedTemporaryFile을 다시 읽을 때 PermissionError 발생 |

전체 시험을 통과했다고 보고하지 않는다. 이 후 추가한 권한·작성자·Flarum 경계 시험은 위 최종309개 관련 회귀시험에 포함된다. OpenAPI export(39 operations)와 `git diff --check`도 확인한다.

## 실제 예약 작업 확인

기존 `ablestack-community-kb`를 중복 생성 없이 갱신했다. ACTIVE, 기존 대상 대화, 한국시간00:00/12:00 주기를 보존했다. 저장된 프롬프트는 [버전 관리 원본](../runbooks/community-scheduled-review-prompt.md)과 동일하다.

공개 API에서 AI 계정40의 실제 이름을 확인하고 읽기 전용 선별 도구를 실행했다.

- #199: 최초 등록2026-11-03으로 신규 기준일 전이지만 명시적 기존 KB 추적 등록으로 포함된다. 현재 선택550과 사람 댓글540/542/548/559를 확인했다. 현 KB에 후속559 보고가 반영된 것을 확인한 뒤 지문 기준을 기록했고, 같은 입력으로 재실행하면 `needsReview=false`이다. 공개 글은 이 작업에서 다시 수정하지 않았다.
- #200: 기존 완료 기록에 지문이 없어 최초 한 번 재검토 대상으로 반환한다. 기존 완료 내용을 자동으로 새 검토 완료로 간주하지 않는다.
- #203: 기존 미완료 접근 대기 단계는 그대로 보존하고 재검토 대상으로 반환한다. 선별 도구만 실행한 것이므로 이 항목을 임의로 완료하지 않는다.
- 새 사람 댓글·내용 수정·해결 선택 변경으로 완료 토론이 다시 검토되는 경우, AI 자신의 KB 편집은 재검토를 유발하지 않는 경우, 페이지 순회·이전 날짜 추적·숨김·잘못된 원본·페이지 루프·HTTP redirect 차단을 자동 시험으로 확인했다.

## 배포 경계와 제한

현재 엔진 변경은 origin 작업 브랜치에서 upstream/main으로 PR 등록하는 범위이다. 자동 병합·운영 엔진 배포·서비스 재시작은 수행하지 않는다. 실제 예약 프롬프트와 로컬 비밀 없는 추적 기록만 이번 요청에 따라 갱신했다.

현재 단일 Gateway worker 안의 잠금으로 동시 중복 처리를 제어한다. 다중 replica/worker의 분산 잠금 보장은 별도 검증 대상이다. 성공 보고 자동 인식은 보수적인 한국어 규칙이며 불명확한 표현·기존 댓글 수정은 예약 재검토가 보완한다. 실모델 답변과 운영 서비스는 병합·승인된 제한 배포 이후 추가 확인해야 한다.
