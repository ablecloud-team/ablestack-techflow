# Issue #20 문서·소스코드 RAG PoC 개정 설계 보고서

> 상태: 개정 설계 완료·제품 책임자 승인 대기
>
> 기준일: 2026-08-03
>
> 관련 PR: 최초 설계 [#47](https://github.com/ablecloud-team/ablestack-techflow/pull/47)

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
| 데이터 | 10개 논리 Table | Compatibility Set·Symbol·Relation 추가 14개 Table |
| 평가 | 30개 질문 | 50개, 코드 질문 20개 이상 |
| P95 | 10초 | 코드 Context를 반영해 12초 |

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

## 9. 하위 Issue 개정

| Issue | 개정 범위 |
|---|---|
| [#41](https://github.com/ablecloud-team/ablestack-techflow/issues/41) | Source Profile·Compatibility Set·Symbol·Relation Schema와 API |
| [#42](https://github.com/ablecloud-team/ablestack-techflow/issues/42) | 7개 저장소·9개 Profile 최신 Head 후보·고정 Commit Fetch·검역·승인 |
| [#43](https://github.com/ablecloud-team/ablestack-techflow/issues/43) | 문서·코드 Parser, Identifier·FTS·Vector, Lineage 삭제 |
| [#44](https://github.com/ablecloud-team/ablestack-techflow/issues/44) | Branch-aware Citation, 문서·코드 답변·보류 |
| [#45](https://github.com/ablecloud-team/ablestack-techflow/issues/45) | 문서·코드 수집·재색인·평가 Flow |
| [#46](https://github.com/ablecloud-team/ablestack-techflow/issues/46) | 50개 Golden Set, Branch Isolation·보안·E2E |

## 10. 검증 자산

- 구조화 계약 Version `1.2`
- 문서·코드 Source, Branch 격리, 실행 금지, Parser, Citation, 삭제, 품질 자동 검증
- README·로드맵·ADR·상세 설계·Runbook
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

## 12. 다음 실행

개정 설계 승인 후 #41부터 구현한다. Provider가 준비되지 않아도 Mock Provider로 Source Profile·API·DB·Fetcher·Parser·Branch Filter 구현을 시작할 수 있다. 실제 Credential은 런타임으로만 제공한다.
