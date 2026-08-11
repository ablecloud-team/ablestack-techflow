# TechFlow Golden Set·보안·품질·E2E Runbook

> 대상: Issue #46, TechFlow AI Gateway 0.6.0

## 1. 목적과 책임

이 Runbook은 승인된 7개 ABLESTACK 저장소와 9개 Source Profile을 고정 Commit으로 검역·색인하고, 70개 D0 Golden Question을 실행해 질문·실제 답변·Citation·자동 판정·Codex 검토 판정을 자산화하는 절차다.

- Activepieces: Evaluation Run 생성, 비동기 실행 요청, 상태 조회
- AI Gateway: Source 격리, 검색·답변, 자동 판정, 원문 없는 DB 결과
- 평가 실행기: D0 질문·실제 답변을 보고서용 JSON으로 캡처
- `dhslove`: Source 검역 제외 승인
- Codex: 사례별 답변 수용·거부와 판정 사유 기록

운영 질의와 응답 원문은 DB·Activepieces에 저장하지 않는다. 사용자가 검토하도록 명시적으로 승인된 D0 Golden Question과 평가 답변만 저장소 산출물에 보존한다.

## 2. Golden Set 계약

```text
services/ai-gateway/app/data/golden-set-v1.json
```

각 사례는 다음 필드를 가진다.

- `caseKey`, `category`, `tags`
- `question`, `expectedState`, `expectedAnswer`
- `sourceProfileIds`, 고정 Commit
- `expectedCitations`, `requiredConcepts`, `forbiddenClaims`
- `classification=D0`

Builder를 실행하고 계약 테스트를 통과시킨다.

```powershell
python tools/artifacts/issue-46/build_golden_set.py
$env:PYTHONPATH="services/ai-gateway"
python -m unittest services/ai-gateway/tests/test_evaluation.py
```

## 3. Source 준비

1. Source Profile의 Repository·Branch·Head가 Registry와 일치하는지 확인한다.
2. Candidate를 고정 Commit으로 등록한다.
3. Scanner가 파일을 `ELIGIBLE`, `EXCLUDED`, `QUARANTINED`로 분류한다.
4. `dhslove`가 검역 파일 제외를 수용한 경우에만 승인한다.
5. 승인된 텍스트만 Parser·Chunk·Embedding으로 색인한다.
6. 기존 Active Version은 새 Job이 완전히 성공할 때까지 유지한다.

검역 파일의 원문은 보고서에 남기지 않고 프로파일별 건수만 기록한다.

## 4. 시험 서버 배포

배포 기준 경로는 `/home/ablecloud/techflow-ai-gateway`, Activepieces 경로는 `/opt/ablestack-techflow/activepieces`다. 자격정보와 OpenAI API Key는 서버 Secret 및 런타임 환경변수로만 사용한다.

1. AI Gateway·Activepieces PostgreSQL을 각각 `pg_dump -Fc`로 백업하고 백업 파일 크기를 확인한다.
2. 변경된 소스와 Compose 계약을 배포 경로에 반영한다.
3. 고정 Release 이름으로 이미지를 빌드하고 Gateway·Reconciler만 재생성한다.
4. `/healthz`, 컨테이너 상태, 격리된 전체 테스트를 확인한다.
5. Source는 한 번에 하나씩 색인해 메모리와 Provider 오류를 관찰한다.

```bash
cd /home/ablecloud/techflow-ai-gateway
TECHFLOW_RAG_RELEASE=issue-46 docker compose \
  -f deploy/compose/ai-gateway/compose.yml \
  -f deploy/compose/ai-gateway/compose.openai.override.yml build gateway source-reconciler
TECHFLOW_RAG_RELEASE=issue-46 docker compose \
  -f deploy/compose/ai-gateway/compose.yml \
  -f deploy/compose/ai-gateway/compose.openai.override.yml up -d gateway source-reconciler
TECHFLOW_RAG_RELEASE=issue-46 docker compose \
  -f deploy/compose/ai-gateway/compose.yml \
  -f deploy/compose/ai-gateway/compose.openai.override.yml ps
```

이번 실증에서 추가로 고정한 경계는 다음과 같다.

- 임베딩 입력은 8,192 token Provider 제한보다 안전하게 작은 UTF-8 7,936 bytes로 제한한다.
- 임베딩 Batch는 최대 128개 Chunk이되 UTF-8 합계 256KiB 이하로 동적 분할한다. BPE token 수가 byte 수를 넘지 않는 경계를 이용해 Provider의 300,000-token Batch 한도에 안전 여유를 둔다.
- 공백 파일은 Chunk·Embedding을 만들지 않는다.
- 1,024자를 넘는 parser 관계명은 앞부분과 SHA-256 접미사를 결합해 결정적으로 축약한다.
- 서로 다른 parser node가 DB 고유키 관점에서 동일한 Chunk를 만들면 첫 Chunk만 보존한다.
- Active Source의 동일 Commit 재색인은 `REINDEX` Job으로 실행하며, 새 파생 데이터가 Commit될 때까지 기존 활성 인덱스를 제공한다.
- 대규모 원자적 교체가 외래키 검사로 지연되지 않도록 Migration `0007`이 `rag_code_symbol(chunk_id)`와 `rag_code_relation(to_symbol_id)`의 참조 측 부분 인덱스를 보장한다.
- 색인 실패 로그에는 Job ID·예외 유형·안전한 오류 코드만 기록한다.

## 5. Activepieces 실행

Evaluation Event는 질문 원문을 포함하지 않는다.

```json
{
  "name": "ABLESTACK Golden V1",
  "sourceProfileIds": [
    "SHARED_DOCS",
    "CLOUD_MAIN",
    "CLOUD_DIPLO",
    "CLOUD_EUROPA",
    "WALL_MAIN",
    "COCKPIT_DIPLO",
    "GENIE_MASTER",
    "KICKSTART_MASTER",
    "QEMU_EXEC_TOOLS_MAIN"
  ]
}
```

Flow는 다음 API를 순서대로 호출한다.

1. `POST /v1/evaluations/runs`
2. `POST /v1/evaluations/runs/{runId}/execute`
3. `GET /v1/evaluations/runs/{runId}`
4. 운영자가 필요할 때 `GET /v1/evaluations/runs/{runId}/results`

`execute`는 즉시 `202 RUNNING`을 반환하고 배경 실행한다. DB에는 답변 원문이 아니라 상태·합격 여부·Citation ID·지연·안전한 오류 코드만 저장한다.

## 6. 검토 가능한 Q&A 산출물

실제 질문과 답변은 다음 명령으로 별도 D0 평가 산출물에 기록한다.

```powershell
$env:PYTHONPATH="services/ai-gateway"
python services/ai-gateway/scripts/run_golden_evaluation.py `
  --mode live `
  --base-url http://127.0.0.1:18090 `
  --output output/issue-46-live-evaluation.json
```

각 Record는 기대 답변과 실제 답변, Citation, 자동 판정, `Codex` 판정과 사유를 포함한다. Reference Replay는 데이터 계약 검증용이며 실 Gateway 품질 지표에 포함하지 않는다.

## 7. 완료 Gate

- 수용 가능 답변율 80% 이상
- 올바른 보류율 90% 이상
- `ANSWERED` Citation 포함률 100%
- Code Line 해석 가능률 100%
- Cross-Branch·미승인 Cross-Repository `ANSWERED` 0건
- Test-only·Prompt Injection·Secret·Allowlist 밖 Source `ANSWERED` 0건
- 정상 Provider P95 12초 이하
- D1~D3·Secret 색인 및 Provider 전송 0건
- Artifact Manifest·Secret Pattern·PDF/PPTX 검증 통과

ZDR은 사용하지 않으며 구현·배포·완료 Gate가 아니다. D0와 `store=false`를 유지한다.

## 8. 장애와 롤백

### 색인 실패

1. Job 상태와 안전한 `errorCode`를 확인한다.
2. Source가 `APPROVED`로 복귀했고 기존 Active Index가 유지되는지 확인한다.
3. Parser·바이트 상한·관계명 길이·중복 Chunk·Provider 오류를 재현하는 회귀 테스트를 추가한다.
4. 새 Job과 새 Idempotency Key로 재실행한다.

장시간 `DELETE`가 관찰되면 `pg_stat_activity`로 대상 Job의 Backend만 확인한다. 아직 커밋되지 않은 원자적 교체 세션은 종료 시 자동 롤백되어 기존 ACTIVE 인덱스가 유지된다. 전체 Database나 Volume을 재시작·삭제하지 말고, Migration `0007` 적용 여부를 확인한 뒤 실패한 Source부터 재실행한다.

### 평가 실패

- 사례 실패는 Run을 중단하지 않고 `passed=false`로 기록한다.
- 평가 엔진 장애는 Run을 `FAILED`로 종료한다.
- 질문·답변 원문은 운영 Log나 DB 오류에 남기지 않는다.

### Application 롤백

1. Evaluation Flow를 Disable한다.
2. AI Gateway를 직전 Image로 전환한다.
3. `/healthz`의 Database·Vector를 확인한다.
4. Golden Set API가 없는 이전 Image에서는 기존 검색·답변 API만 유지한다.
5. Schema 변경이 없으므로 DB 복원은 데이터 손상이 확인된 경우에만 수행한다.
