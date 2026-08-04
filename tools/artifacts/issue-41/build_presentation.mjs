import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const ROOT = path.resolve(process.argv[2]);
const TMP = `${ROOT}/tmp/issue-41-artifacts`;
const STARTER = `${TMP}/template-starter.pptx`;
const OUTPUT = `${ROOT}/output/presentation/techflow-ai-gateway-foundation.pptx`;
const RENDER_DIR = `${TMP}/final-rendered`;
const LAYOUT_DIR = `${TMP}/final-layout`;

const edits = [
  [1, "ABLESTACK TECHFLOW · ISSUE #20 · REVISED", "ABLESTACK TECHFLOW · ISSUE #41 · IMPLEMENTED"],
  [1, "문서·코드 + OpenAI\nRAG PoC 개정 설계", "AI Gateway API·DB\n기반 구현 완료"],
  [1, "Local Retrieval · OpenAI Responses / Embeddings · Tool 0", "11 APIs · 15 Tables · 3 Provider Profiles · Mock Only"],
  [1, "TechFlow · Activepieces CE · 2026-08-03", "TechFlow · AI Gateway 0.1.0 · 2026-08-04"],

  [2, "ABLESTACK 7개 저장소의 39,836개 파일을 분석 대상으로 확정했습니다", "11개 API와 15개 테이블을 실제 서버에서 검증했습니다"],
  [2, "Cloud 세 Branch와 5개 구성 저장소를 독립 색인하고 승인 조합만 검색합니다.", "외부 호출 없이 API·DB·보안·배포 계약을 구현하고 실제 Canary를 통과했습니다."],
  [2, "공식 문서", "구현 계약"],
  [2, "276 Markdown\nSHARED_DOCS\nD0 Public", "FastAPI 11 Ops\nPostgreSQL 15 Tables\n3 Provider Profiles"],
  [2, "제품 소스코드", "실서버 결과"],
  [2, "6 Repositories\n8 Code Profiles\n39,560 Files", "2/2 Healthy\nCanary PASS\nLeast Privilege PASS"],
  [2, "개정 범위", "완료 판정"],
  [2, "9 Profiles  |  39,836 Files  |  15 Tables  |  50 Golden Questions", "58 Unit Tests  |  3 Validator Tests  |  Secrets 0  |  Provider Calls 0"],

  [3, "실행·분석·저장을 분리해 소스코드를 안전하게 다룹니다", "Activepieces는 흐름, AI Gateway는 정책과 상태를 소유합니다"],
  [3, "Activepieces는 오케스트레이션하고 Fetcher·AI Gateway가 고정 Commit을 정적으로 분석합니다.", "#41은 실행 엔진과 RAG 상태·권한·Provider 계약의 책임 경계를 코드로 고정했습니다."],
  [3, "Change Detection\nApproval · Job\nEvaluation Schedule", "Approval · Reindex Flow\nJob Orchestration\nProvider Secret 0"],
  [3, "Pinned Fetcher\nParser · Retrieval\nOpenAI Adapters", "Source · Compatibility\nIdempotency · Validation\nMock Adapters"],
  [3, "FTS · pg_trgm\npgvector\nSymbol · Lineage", "15 RAG Tables\npgvector · pg_trgm\nAudit Metadata"],
  [3, "제품 Gate  |  Branch 격리 · 로컬 검색 · Responses API · Tool 0", "제품 Gate  |  D0 Only · 승인 Commit · 멱등성 · 근거 없는 성공 금지"],

  [4, "저장소와 코드는 서로 다른 분석 Profile을 사용합니다", "15개 테이블이 RAG 수명주기를 단계별로 분리합니다"],
  [4, "코드는 Symbol·Line Range를 보존하고 Test만으로 답변하지 않습니다.", "Source부터 Provider 감사까지 상태·삭제·평가를 독립 추적합니다."],
  [4, "Retrieval 전에 Source Profile·Compatibility Set·Branch·Commit을 적용합니다.", "vector(3072) · FTS · pg_trgm · 3 NOLOGIN Roles · PUBLIC 권한 회수"],

  [5, "Source는 등록부터 삭제까지 여섯 Gate를 통과합니다", "11개 API는 승인·작업·질의 상태를 명시적으로 분리합니다"],
  [5, "새 Branch Head는 후보일 뿐이며 승인·전체 색인 성공 전에는 활성화하지 않습니다.", "모든 v1 요청은 Correlation ID를, 변경 요청은 Idempotency Key를 요구합니다."],
  [5, "Register", "Register"],
  [5, "Source Owner", "TechFlow Core"],
  [5, "9 Profiles", "Source Create · Get"],
  [5, "Pin", "Approve"],
  [5, "Reviewer", "Reviewer"],
  [5, "Branch · Commit", "Commit · D0 승인"],
  [5, "Quarantine", "Ingestion"],
  [5, "Fetcher", "AI Gateway"],
  [5, "Secret · Binary", "202 Job · Idempotent"],
  [5, "Parse", "Compatibility"],
  [5, "AI Gateway", "Policy"],
  [5, "Symbol · Fallback", "승인 조합만"],
  [5, "Index", "Query"],
  [5, "Worker", "Mock Provider"],
  [5, "FTS · ID · Vector", "ABSTAINED · No Call"],
  [5, "Delete", "Evaluate · Delete"],
  [5, "Lineage Job", "Audit Job"],
  [5, "Exclude Now · ≤ 7d", "결과 · 철회 추적"],

  [6, "로컬 검색 결과만 OpenAI API에 전달합니다", "Mock Provider로 실제 OpenAI 호출 전 계약을 고정했습니다"],
  [6, "원본 저장소는 내부에 유지하고 최종 D0 Chunk와 Citation만 전송합니다.", "세 Provider Profile과 구조화 응답·3,072차원 Vector를 결정론적으로 검증합니다."],
  [6, "Channel / Flow", "TechFlow Core"],
  [6, "Question\nProfile / Set", "Correlation\nIdempotency"],
  [6, "Gate · RRF\nRoute · Validate", "Profile · D0 Gate\nValidate · Store"],
  [6, "Docs · Symbols\nFTS · ID · Vector", "Source · Jobs\nAudit Metadata"],
  [6, "OpenAI API", "Mock Provider"],
  [6, "Responses\nTerra / Sol", "Structured JSON\nDeterministic"],
  [6, "Embeddings API", "Mock Embeddings"],
  [6, "text-embedding-3-large", "3,072 Dimensions"],
  [6, "TechFlow 내부", "제품 내부"],
  [6, "OpenAI 경계", "Mock 경계"],

  [7, "Terra 기본, Sol 승격을 호출 전에 결정합니다", "보안 기본값과 검증 가능한 실패가 기본 동작입니다"],
  [7, "Base", "Host"],
  [7, "Terra · medium", "10001:10001"],
  [7, "일반 기술지원\n단일 Profile\n한 번 호출", "Read-only FS\nCap Drop ALL\nNo Privilege"],
  [7, "Escalate", "Net"],
  [7, "Sol · high", "DB Internal"],
  [7, "소스 충돌\n복수 구성요소\n규칙 기반", "DB Port 0\nLocalhost Bind\nEdge 분리"],
  [7, "Guard", "Provider"],
  [7, "Tool 0", "D0 Only"],
  [7, "store=false\nStructured JSON\nCitation 재검증", "store=false\nTool 0\nRaw Payload 0"],
  [7, "15 Tables", "58 Tests"],
  [7, "29 Contract Tests", "Canary PASS"],
  [7, "No Double Call", "Secrets 0"],

  [8, "개정 설계·운영·검증을 같은 제품 자산으로 유지합니다", "코드·운영·검증 증적을 하나의 제품 자산으로 관리합니다"],
  [8, "Issue #20의 안정적인 파일명과 링크는 유지하고 내용·체크섬을 갱신합니다.", "다음 운영자가 같은 기반을 배포·검증·롤백할 수 있도록 모든 절차를 저장소에 남겼습니다."],
  [8, "설계 자산", "구현 자산"],
  [8, "ADR-0008 · 0009\nDetailed Plan\nContract v1.3", "FastAPI Service\n15-table Migration\nOpenAPI Contract"],
  [8, "Responses · Embeddings\nData Control Gate\nDeploy · Rollback", "Compose · Secrets\nDeploy · Verify\nRollback Runbook"],
  [8, "29 Contract Tests\nReport · Deck\n15-file Manifest", "Decision JSON\nReport · Deck\nSHA-256 Manifest"],
  [8, "Issue #20  |  Local RAG · OpenAI Responses · Compatibility-aware", "Issue #41  |  API · DB · Mock Provider · Test Server Deployment"],

  [9, "OpenAI 런타임을 #41·#43·#44로 나눠 구현합니다", "#41 기반을 완료했고 #42 Source 승인 단계로 이동할 수 있습니다"],
  [9, "기존 이슈 번호와 의존 순서를 유지하면서 완료 기준을 개정합니다.", "실제 Source 수집과 OpenAI 호출은 승인된 후속 이슈에서만 활성화합니다."],
  [9, "#41 Foundation", "#41 Complete"],
  [9, "Provider Profiles\n15 Tables", "API · DB\nMock · Deploy"],
  [9, "#42 Intake", "#42 Intake"],
  [9, "9 Profiles\nPinned Fetch", "9 Profiles\nApprove · Fetch"],
  [9, "Embeddings\nFTS · ID · Vector", "Embedding\nFTS · ID · Vector"],
  [9, "Responses · Route\nCitation Validate", "Responses · Route\nCitation Validate"],
  [9, "후속 = #45 Activepieces Flow → #46 모델·비용·품질·보안 E2E", "후속 = #45 Activepieces Flow → #46 품질·보안·비용·E2E"],

  [10, "OpenAI 런타임 설계 승인 요청", "Issue #41 완료"],
  [10, "OpenAI 런타임을 승인하면\n#41부터 구현합니다.", "AI Gateway 기반이\n배포·검증·롤백 가능한 상태입니다."],
  [10, "ISSUE #20 · REVISED", "ISSUE #41 · COMPLETE"],
  [10, "9 PROFILES · OPENAI RESPONSES · LOCAL RAG · TOOL 0", "11 API · 15 TABLES · 3 PROFILES · CANARY PASS · PROVIDER CALL 0"],
  [10, "ABLESTACK TechFlow · OpenAI Runtime & Source Code RAG", "ABLESTACK TechFlow · AI Gateway Foundation"],
  [10, "Issue #20 · 2026-08-03", "Issue #41 · 2026-08-04"],
];

const tableRows = [
  ["Schema Group", "Tables", "Key Control", "Verification"],
  ["Source", "source · version", "Commit pin · D0", "Approval state"],
  ["Compatibility", "set · set_source", "Approved members", "Cross-repo gate"],
  ["Ingestion", "job · chunk", "Idempotency", "Job lifecycle"],
  ["Embedding", "profile · embedding", "vector(3072)", "Profile lock"],
  ["Code Graph", "symbol · relation", "Path · Lineage", "Static metadata"],
  ["Deletion", "deletion_ledger", "Withdraw · SLO", "Audit trail"],
  ["Evaluation", "case · run · result", "Golden run", "Result lineage"],
  ["Provider", "provider_call", "Safe metadata", "Raw payload 0"],
];

const notesBySlide = {
  1: "Issue #41의 AI Gateway API·DB·Mock Provider 기반 구현 완료를 요약합니다.",
  2: "11개 API, 15개 테이블, 3개 Profile과 실제 서버 Canary를 완료했습니다.",
  3: "Activepieces는 흐름을, AI Gateway는 정책·상태·멱등성을, PostgreSQL은 권위 데이터를 소유합니다.",
  4: "15개 논리 테이블은 Source, 수집, 검색, 삭제, 평가, Provider 감사 수명주기를 분리합니다.",
  5: "API는 승인, Compatibility, Job, 질의, 평가, 철회를 명시적 상태로 구분합니다.",
  6: "#41은 실제 OpenAI 호출 없이 Mock Responses와 Mock Embeddings로 계약만 검증합니다.",
  7: "Non-root, Read-only, 최소권한 Network, D0 Only와 안전한 로그가 기본값입니다.",
  8: "코드, Migration, OpenAPI, Compose, Runbook, 보고서와 Manifest를 일관된 자산으로 관리합니다.",
  9: "다음 실행 단위는 #42 Source 승인·수집이며, Retrieval과 OpenAI 호출은 #43·#44에서 활성화합니다.",
  10: "Issue #41은 구현·배포·검증·롤백 가능한 상태로 완료됐습니다.",
};

const sources = [
  "- docs/reports/issue-41-ai-gateway-foundation-validation.md",
  "- docs/decisions/techflow-ai-gateway-foundation.json",
  "- docs/runbooks/ai-gateway-foundation.md",
  "- services/ai-gateway/openapi/techflow-ai-gateway-v1.json",
  "- https://fastapi.tiangolo.com/advanced/events/",
  "- https://fastapi.tiangolo.com/deployment/docker/",
  "- https://www.psycopg.org/psycopg3/docs/advanced/pool.html",
  "- https://github.com/pgvector/pgvector",
  "- https://github.com/ablecloud-team/ablestack-techflow/issues/41",
];

async function saveBlob(file, blob) {
  await fs.mkdir(path.dirname(file), { recursive: true });
  await fs.writeFile(file, new Uint8Array(await blob.arrayBuffer()));
}

async function main() {
  const presentation = await PresentationFile.importPptx(await FileBlob.load(STARTER));
  const snapshot = await presentation.inspect({ kind: "slide,textbox,table,notes", maxChars: 500000 });
  const records = snapshot.ndjson.split(/\r?\n/).filter(Boolean).map(JSON.parse);

  for (const [slideNumber, oldText, newText] of edits) {
    const hit = records.find((record) => record.kind === "textbox" && record.slide === slideNumber && record.text === oldText);
    if (!hit) throw new Error(`Missing inherited edit target slide=${slideNumber} text=${oldText}`);
    presentation.resolve(hit.id).text = newText;
  }

  const tableRecord = records.find((record) => record.kind === "table" && record.slide === 4);
  if (!tableRecord) throw new Error("Slide 4 inherited table not found");
  const table = presentation.resolve(tableRecord.id);
  for (let row = 0; row < tableRows.length; row += 1) {
    for (let column = 0; column < tableRows[row].length; column += 1) {
      table.cells.set(row, column, tableRows[row][column]);
    }
  }

  for (const noteRecord of records.filter((record) => record.kind === "notes")) {
    presentation.resolve(noteRecord.id).setText([
      notesBySlide[noteRecord.slide],
      "[Sources]",
      ...sources,
      "[/Sources]",
    ].join("\n"));
  }

  await fs.mkdir(RENDER_DIR, { recursive: true });
  await fs.mkdir(LAYOUT_DIR, { recursive: true });
  for (const [index, slide] of presentation.slides.items.entries()) {
    const stem = `slide-${String(index + 1).padStart(2, "0")}`;
    await saveBlob(`${RENDER_DIR}/${stem}.png`, await presentation.export({ slide, format: "png", scale: 1 }));
    await fs.writeFile(`${LAYOUT_DIR}/${stem}.layout.json`, await (await slide.export({ format: "layout" })).text(), "utf8");
  }
  await saveBlob(`${TMP}/final-montage.webp`, await presentation.export({ format: "webp", montage: true, scale: 1 }));
  const finalInspect = await presentation.inspect({ kind: "deck,layout,slide,textbox,table,notes", maxChars: 500000 });
  await fs.writeFile(`${TMP}/final-inspect.ndjson`, `${finalInspect.ndjson}\n`, "utf8");
  await fs.mkdir(path.dirname(OUTPUT), { recursive: true });
  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(OUTPUT);
  console.log(OUTPUT);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
