# Issue #20 문서·소스코드 RAG PoC 개정 설계 보고서

> 상태: 개정 설계 완료·제품 책임자 승인 대기
>
> 기준일: 2026-08-03
>
> 관련 PR: 최초 설계 [#47](https://github.com/ablecloud-team/ablestack-techflow/pull/47), 개정 설계 [#48](https://github.com/ablecloud-team/ablestack-techflow/pull/48)

## 1. 개정 결론

최초 설계의 공개 Source는 `ablestack-docs/docs/**/*.md`만 의미했다. 제품 기술지원 Assist가 실제 구현을 설명하려면 공식 문서만으로 부족하다는 제품 책임자 의견을 반영해 ABLESTACK 제품을 구성하는 6개 소스 저장소까지 P1 분석 범위에 포함했다.

총 7개 저장소를 9개 Source Profile로 독립 색인한다. `ablestack-cloud`는 `main`, `ablestack-diplo`, `ablestack-europa` 최신 Head를 각각 추적하되 승인 Commit만 활성화하고, 세 Branch는 절대 섞지 않는다. 서로 다른 저장소의 근거도 승인된 Compatibility Set에서만 결합한다.

## 2. 실제 Source 조사 결과

| Source Profile | Repository·Branch | Commit | 전체 | 허용 | Production / Test |
|---|---|---|---:|---:|---:|
| `SHARED_DOCS` | `ablestack-docs/master` | `50d50ad6c8c5` | 4,236 | 276 | - |
| `CLOUD_MAIN` | `ablestack-cloud/main` | `a873fb1ff436` | 10,926 | 10,502 | 8,673 / 1,829 |
| `CLOUD_DIPLO` | `ablestack-cloud/ablestack-diplo` | `87beae809aa7` | 10,977 | 10,551 | 8,831 / 1,720 |
| `CLOUD_EUROPA` | `ablestack-cloud/ablestack-europa` | `4787b6918bfa` | 11,913 | 11,447 | 9,563 / 1,884 |
| `WALL_MAIN` | `ablestack-wall/main` | `f27b3f1b0b35` | 7,421 | 6,557 | 5,156 / 1,401 |
| `COCKPIT_DIPLO` | `ablestack-cockpit-plugin/ablestack-diplo` | `201845307706` | 728 | 213 | 211 / 2 |
| `GENIE_MASTER` | `ablestack-genie/master` | `3e3c5c364f5c` | 34 | 34 | 34 / 0 |
| `KICKSTART_MASTER` | `ablestack-kickstart/master` | `ffe24390544d` | 30 | 18 | 18 / 0 |
| `QEMU_EXEC_TOOLS_MAIN` | `ablestack-qemu-exec-tools/main` | `a4b9bd60bb93` | 314 | 238 | 198 / 40 |

Git Tree 전체 46,579개 Blob 중 39,836개가 확장자·경로·1 MiB 정책을 통과했다. GitHub License API에서 `ablestack-cloud` Apache-2.0, `ablestack-wall` AGPL-3.0을 확인했다. 다른 저장소의 License Metadata 미검출·`NOASSERTION`은 기록하되 사내 분석 구현을 차단하지 않는다.

## 3. 주요 설계 변경

| 영역 | 최초 설계 | 개정 설계 |
|---|---|---|
| Source | 문서 276개 | 문서 + 6개 코드 저장소, 9개 Profile, 39,836개 |
| 격리 | 제품·Version Metadata | Source Profile·Compatibility Set·Branch·Commit 선필터 |
| Chunk | Markdown Heading | 문서 Heading + Code Symbol + Schema Block |
| 검색 | FTS + Vector | FTS + Identifier/Trigram + Vector |
| Citation | Source·Section·Chunk | Repository·Branch·Commit·Path·Line·Symbol |
| Test | 별도 정책 없음 | 보강 근거, 단독 답변 금지 |
| 데이터 | 10개 논리 Table | Compatibility Set·Symbol·Relation·Provider Call 추가 15개 Table |
| 평가 | 30개 질문 | 50개, 코드 질문 20개 이상 |
| P95 | 10초 | 코드 Context를 반영해 12초 |

## 3.1 OpenAI 런타임 보강 결론

기존 설계는 AI Gateway가 Provider Adapter를 소유한다고만 정의해 문서·소스코드와 AI Engine이 실제로 어떤 API와 데이터 경계로 연결되는지 부족했다. 구현 전에 다음과 같이 확정했다.

| 방식 | 결정 | 역할 |
|---|---|---|
| Responses API | 채택 | TechFlow 고객 질의의 구조화 답변 생성 |
| Embeddings API | 채택 | 승인된 Chunk와 Query Vector 생성 |
| Batch API | 조건부 채택 | 최초 대량 색인·전체 재색인·평가 |
| ChatGPT Work | 런타임 제외 | 사람 중심 분석·보고·평가 자산 작성에 선택 사용 |
| Codex | 런타임 제외 | 개발·코드 리뷰·오프라인 평가 케이스 작성에 선택 사용 |
| Agents SDK·Hosted Tool | P1 제외 | 현재 제품 경로는 Tool 없는 단일 구조화 답변 |

기본 답변은 `gpt-5.6-terra/medium`, 검색 단계에서 문서·코드 충돌 또는 복수 구성요소 분석이 확인된 질의만 `gpt-5.6-sol/high`로 호출 전에 승격한다. Embedding 기준선은 `text-embedding-3-large/3072`이며 #43의 Golden Set에서 저차원·Small 대안을 비교한다.

원본 Repository는 OpenAI File·Vector Store·ChatGPT Project에 업로드하지 않는다. TechFlow가 고정 Commit 기준으로 로컬 Parse·Hybrid Retrieval을 수행하고, 최종 최대 10개 D0 Chunk와 Citation Metadata만 Responses API에 전달한다. 요청은 `store=false`, `background=false`, Tool 0개, Structured Output을 강제하고 반환 Citation을 Gateway가 다시 검증한다.

제품 책임자의 2026-08-10 결정에 따라 Zero Data Retention은 사용하지 않으며 적격성·승인·적용 상태를 구현·배포 Gate에서 제외한다. `store=false`는 애플리케이션 수준 데이터 최소화 통제로 유지하고 P1은 현재 구현 경계에 따라 D0만 전송한다. D1 이상 확대는 TechFlow 제품 보안심사로 결정한다.

## 4. 안전한 코드 수집

- Allowlist Repository·Branch·Commit의 Tree·Text Blob만 읽는다.
- Hook, Git LFS Smudge, Submodule, Build, Test와 Source Code를 실행하지 않는다.
- `target`, `build`, `dist`, `node_modules`, `vendor`, `third_party`, `generated`, `gen`을 제외한다.
- Binary, Minified, 1 MiB 초과, 비정상 Encoding, Secret·개인정보 검출 파일을 색인하지 않는다.
- 공개 코드도 검역을 생략하지 않는다.
- 승인되지 않은 새 Branch Head는 후보 Version에 머물며 자동 활성화하지 않는다.

AI Tool 실행 금지와 고정 Source Fetch는 분리했다. Fetcher는 승인된 입력에 대한 미리 정의된 읽기 동작만 수행하고 AI가 명령을 생성하지 않는다.

## 5. 코드 분석 범위

Tree-sitter를 사용해 Class, Method, Function, Vue Component와 주요 선언을 Symbol 단위로 분할한다. Package, Import, Annotation, Signature, Doc Comment와 Line Range를 보존한다. Parser가 실패하면 160 Line·Overlap 20의 결정적 Fallback을 사용한다.

PoC는 Import, Inheritance, Declaration과 정적으로 확인 가능한 Reference Edge를 저장한다. Build가 필요한 완전한 Call Graph와 동적 실행 분석은 범위에서 제외한다.

## 6. 검색·답변 계약

1. Source Profile·Compatibility Set·Branch·Commit을 후보 생성 전에 적용한다.
2. FTS 20, Identifier 20, exact cosine 30개 후보를 생성한다.
3. RRF `k=60`으로 결합하고 Test Chunk는 0.6 Weight를 적용한다.
4. 최종 10개, Source Version당 4개로 제한한다.
5. Cross-Branch, 미승인 Cross-Repository, Test-only, Branch 미지정, Citation 불일치는 `ABSTAINED`다.
6. `ANSWERED`는 Source Profile·Compatibility Set과 Code Line Citation을 포함한다.

문서와 코드가 충돌하면 사용자가 지정한 Branch의 구현을 기준으로 설명하면서 차이를 표시한다. 제품 Profile을 알 수 없으면 임의 선택하지 않는다.

## 7. 데이터·삭제

기존 Source·Version·Job·Chunk·Embedding·Deletion·Evaluation Table에 다음을 추가했다.

- `rag_compatibility_set`: 승인된 제품·구성요소 조합
- `rag_compatibility_set_source`: Source Profile·Commit Membership
- `rag_code_symbol`: Language, Package, Qualified Name, Signature, Line Range
- `rag_code_relation`: Import, Inheritance, Declaration, Reference
- `rag_provider_call`: Query·Evaluation, Provider Request·Response ID, Model Profile, Token·Latency·상태·오류; 원문 제외

Source Profile 철회 시 Chunk, Embedding, Symbol, Relation, Cache와 Evaluation Link를 즉시 검색에서 제외한다. 테스트 목표는 15분, 정책 상한은 7일이며 복구 후 Deletion Ledger를 재적용한다.

## 8. 품질 Gate

| 지표 | 기준 |
|---|---:|
| Golden Question | 50개 이상 |
| Code Question | 20개 이상 |
| `ANSWERED` Citation | 100% |
| Code Citation 해석 가능 | 100% |
| 수용 가능 답변 | 80% 이상 |
| 올바른 보류 | 90% 이상 |
| Cross-Branch Evidence | 0건 |
| 미승인 Cross-Repository Evidence | 0건 |
| Test-only `ANSWERED` | 0건 |
| D1~D3·Secret 색인 | 0건 |
| 철회 파생 데이터 | 0건 |
| Structured Output·Citation 사후 검증 | 100% |
| Provider Tool 호출 | 0건 |
| 승인 없는 Model Profile 변경 | 0건 |

## 9. 하위 Issue 개정

| Issue | 개정 범위 |
|---|---|
| [#41](https://github.com/ablecloud-team/ablestack-techflow/issues/41) | Source·Compatibility·Provider Profile, Symbol·Relation·Provider Call Schema와 API |
| [#42](https://github.com/ablecloud-team/ablestack-techflow/issues/42) | 7개 저장소·9개 Profile 최신 Head 후보·고정 Commit Fetch·검역·승인 |
| [#43](https://github.com/ablecloud-team/ablestack-techflow/issues/43) | 문서·코드 Parser, OpenAI Embeddings, Identifier·FTS·Vector, Lineage 삭제 |
| [#44](https://github.com/ablecloud-team/ablestack-techflow/issues/44) | OpenAI Responses·모델 라우팅·Structured Output·Branch-aware Citation·보류 |
| [#45](https://github.com/ablecloud-team/ablestack-techflow/issues/45) | 문서·코드 수집·재색인·평가 Flow |
| [#46](https://github.com/ablecloud-team/ablestack-techflow/issues/46) | 50개 Golden Set, Branch Isolation·보안·E2E |

## 10. 검증 자산

- 구조화 계약 Version `1.3`
- 문서·코드 Source, Branch 격리, 실행 금지, Parser, Citation, 삭제, 품질 자동 검증
- README·로드맵·ADR·상세 설계·Runbook
- OpenAI 런타임 ADR-0009와 Provider 요청·보존·모델 라우팅 계약
- 개정 보고서 PDF
- 개정 프레젠테이션 PPTX와 PDF
- Artifact Manifest·Page/Slide·Link·Secret Pattern 검증

## 11. 제품 책임자 승인 항목

1. 7개 저장소·9개 Source Profile 포함
2. Cloud main·Diplo·Europa 독립 색인과 Cross-Branch Fusion 금지
3. 승인된 Compatibility Set에서만 Cross-Repository Fusion 허용
4. 확장된 Code·UI·Schema·Provisioning Allowlist와 Generated·Binary 제외
5. Tree-sitter Symbol Chunk와 결정적 Fallback
6. Test Code 보강 근거·단독 답변 금지
7. Repository·Branch·Commit·Path·Line·Symbol Citation
8. 50개 Golden Set 중 Code 질문 20개 이상 및 6개 코드 저장소별 최소 1개
9. Source Code Build·Test·실행 제외
10. Responses API·Embeddings API를 제품 런타임으로 사용
11. `gpt-5.6-terra/medium` 기본과 규칙 기반 `gpt-5.6-sol/high` 승격
12. `text-embedding-3-large/3072` PoC 기준선
13. OpenAI File·Vector Store·Agent Tool을 P1에서 사용하지 않음
14. Zero Data Retention 미사용과 향후 Gate 제외, 데이터 등급 확대 시 TechFlow 제품 보안심사 적용
15. ChatGPT Work·Codex는 운영·개발 보조이며 제품 런타임이 아님

## 12. 다음 실행

OpenAI 런타임 결정을 포함한 개정 설계 승인 후 #41부터 구현한다. #41은 Provider Profile과 `rag_provider_call`까지 Mock Adapter로 구현하고, 실제 Embeddings·Responses 호출은 #43·#44에서 진행한다. 실제 Credential은 런타임으로만 제공한다.

## 13. 참고 자료

- [ADR-0009 OpenAI 런타임 통합 및 모델 라우팅](../adr/0009-openai-runtime-integration.md)
- [OpenAI Model Guidance](https://developers.openai.com/api/docs/guides/latest-model)
- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [OpenAI Vector Embeddings](https://developers.openai.com/api/docs/guides/embeddings)
- [OpenAI API Data Controls](https://platform.openai.com/docs/models/default-usage-policies-by-endpoint)
