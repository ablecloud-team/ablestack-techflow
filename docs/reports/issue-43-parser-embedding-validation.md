# Issue #43 Parser·Chunk·Embedding·검색 구현 완료 보고서

## 1. 완료 판정

Issue #43의 구현·시험 서버 배포·GENIE Canary·검색·재시작 영속성·격리 삭제 Drill·문서화·PDF/PPTX 자산화를 완료했습니다.

| 항목 | 결과 |
|---|---|
| Gateway | 0.3.0, Healthy |
| API | 21 Operation |
| DB | 19 Table, Issue #43 Column 8 |
| Parser | 13종 Prefetch, 8 Parsed·26 Fallback |
| GENIE Source | 34 / 34 File |
| Index | 64 Chunk·64 Embedding·15 Symbol·45 Relation |
| Retrieval | 상위 10개, Commit·Path·Line 고정 인용 |
| Provider | Mock, 외부 OpenAI 호출 0 |
| 삭제 Drill | 64·64·15·45 삭제, 잔여 0 |
| 기존 서비스 | Activepieces 6개 Container 모두 Healthy |
| 저장소 검증 | 87 Test + 4 Subtest 통과 |

## 2. 구현 결과

### Parser와 Chunk

- Markdown은 Heading 경계를 보존합니다.
- Python·Java·JavaScript·TypeScript·Vue·Go·C/C++·C#·Shell·Ruby·Rust 계열은 Tree-sitter를 사용합니다.
- Parser 오류나 미지원 형식은 최대 160 Line, Overlap 20의 Fallback을 사용합니다.
- Chunk는 최대 24 KiB이며 UUIDv5와 Content Hash로 결정론적으로 식별합니다.
- Repository 파일을 Import·Build·Test·Shell 실행하지 않습니다.

### Embedding

- Profile: `OPENAI_EMBEDDING_V1`
- Model: `text-embedding-3-large`
- Dimension: 3072
- SDK: 공식 OpenAI Python SDK 2.53.0
- Batch: 최대 128, 서버 기본 64
- Secret: Runtime Secret File 참조만 허용
- 감사: Provider·요청/반환 Model·Request ID·Token·Latency만 저장

이번 실증은 실 API Key 없이 Mock Adapter를 사용했습니다. 따라서 외부 Provider 호출은 0건이며, 실 OpenAI Canary는 운영 Key 주입 승인 후 별도 수행합니다.

### Hybrid Retrieval

Source Scope와 `ACTIVE` 상태를 후보 생성 전에 적용합니다. FTS 20, Identifier 20, exact cosine 30을 만들고 RRF `k=60`으로 결합해 최대 10개를 반환합니다. `TEST_CODE`는 단독 근거의 과대평가를 막기 위해 Weight 0.6을 적용합니다.

응답은 다음 Lineage를 포함합니다.

```text
repository / branch / commit / path / startLine / endLine / symbol / chunkId
```

## 3. 실증 Source

```text
Profile: GENIE_MASTER
Repository: ablecloud-team/ablestack-genie
Branch: master
Commit: 3e3c5c364f5c7261b07d49fcbcd4f3605b91f3b1
Source Version: 059ae7d0-7d6c-4fb3-a0ed-fa3eab1f6cae
Eligible: 34
```

질의 결과 상위 인용은 `genie-shell/README.md`의 AWX·Automation Controller 구성 절차를 승인 Commit의 Line Range로 반환했습니다.

## 4. 실패와 보상 정책 검증

서버 최초 실행에서 DB Row Alias와 JSONB Adapter 결함 2건을 발견했습니다. 두 경우 모두 Job은 `FAILED`, Source는 `APPROVED`로 복귀했고 활성 Chunk는 0건을 유지했습니다. 수정 후 새 Job·새 멱등키로 재실행해 34 / 34 활성화에 성공했습니다.

이 결과로 다음 정책을 확인했습니다.

- 부분 성공은 활성화하지 않습니다.
- 기존 Active Version은 새 Version 전체 성공 전까지 유지합니다.
- 실패 Source는 재검토 가능한 `APPROVED`로 복귀합니다.
- 오류는 안전한 코드만 남기고 원문·Secret을 기록하지 않습니다.

## 5. 삭제 Drill

Live GENIE Index를 보존하기 위해 `techflow_rag_issue43_drill` 격리 DB를 생성해 삭제를 시험하고, 종료 시 정확한 임시 DB만 제거했습니다.

| 파생 데이터 | 삭제 수 |
|---|---:|
| Chunk | 64 |
| Embedding | 64 |
| Symbol | 15 |
| Relation | 45 |
| 잔여 Chunk | 0 |

Deletion Ledger는 `SUCCEEDED`와 각 삭제 수를 기록했습니다.

## 6. 배포와 복구 자산

- 배포 경로: `/home/ablecloud/techflow-ai-gateway`
- Compose Release: `issue-43`
- Gateway Image ID: `sha256:d767e54b31cf9532f876c63d212acd452f4d1220e3d6690afc5e61036b7fdd3e`
- Runtime: `10001:10001`, Read-only Root FS
- 백업: `/home/ablecloud/techflow-ai-gateway/backups/issue43-20260805T1444KST`
- Root: 1,005 GiB, 사용 14 GiB, 가용 950 GiB

Gateway 재시작 후 Health와 34 / 34·64 / 64 활성 Index를 다시 확인했습니다. Activepieces 6개 기존 Container는 모두 Healthy를 유지했습니다.

## 7. 성능 전환 기준

현재 Active Chunk는 64개이므로 exact cosine이 단순하고 재현성이 높습니다. HNSW는 Active Chunk 50,000개 도달 전까지 비활성화합니다. 이후 동일 Golden Set에서 Recall 손실 2%p 이하와 P95 개선을 함께 검증한 뒤 Profile별 전환을 제안합니다.

## 8. 검증 명령과 결과

```text
pytest: 87 passed, 4 subtests passed
OpenAPI: 21 operations
Migration manifest: 12 files
Repository validator: issue43=valid
Presentation: 10 slides, no overflow, template fidelity pass
```

## 9. 다음 단계

다음 구현 대상은 Issue #44입니다.

1. OpenAI Responses Adapter
2. Structured Output과 Citation 사용 검증
3. 근거 부족·충돌·Test-only 질문의 `ABSTAINED` 판정
4. Terra 기본·Sol 제한적 승격 Routing
5. 운영 API Key를 사용한 실 Embedding Canary 증적

Issue #43은 검색 근거 계층까지 완료했으며 답변 생성은 아직 수행하지 않습니다.
