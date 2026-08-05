import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

const root = path.resolve(process.argv[2] ?? process.cwd()).replaceAll("\\", "/");
const artifactEntry =
  process.env.CODEX_ARTIFACT_TOOL_PATH ??
  `${root}/tmp/issue43-presentation/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs`;
const { FileBlob, PresentationFile } = await import(pathToFileURL(artifactEntry));
const starter = `${root}/tmp/issue43-presentation/template-starter.pptx`;
const finalPptx = `${root}/output/presentation/techflow-parser-embedding.pptx`;
const renderDir = `${root}/tmp/issue43-presentation/final-renders`;
const layoutDir = `${root}/tmp/issue43-presentation/final-layout`;

const copy = [
  [
    "ABLESTACK TECHFLOW · ISSUE #43",
    "Parser·Chunk·Embedding·검색\n구현 및 서버 실증 완료",
    "34 Files · 64 Chunks · 64 Embeddings · 10 Source-pinned Results",
    "GENIE master@3e3c5c · Mock Provider · OpenAI Call 0 · 2026-08-05",
  ],
  [
    "승인된 GENIE 소스를 검색 가능한 근거로 전환했습니다",
    "02",
    "모든 수치는 시험 서버의 활성 인덱스와 격리 삭제 Drill 결과입니다.",
    "34", "ELIGIBLE FILES", "승인 Commit의 대상 파일 전부",
    "64", "CHUNKS", "15 Symbol · 45 Relation · 64 Vector",
    "10", "TOP RESULTS", "Repository·Branch·Commit·Path·Line",
  ],
  [
    "원문 실행 없이 Parser·Embedding·검색 책임을 분리했습니다",
    "03",
    "1", "PARSE", "검증된 UTF-8 Text만 처리\nTree-sitter 실패 시 결정론적 Fallback",
    "2", "EMBED", "공식 SDK Adapter\ntext-embedding-3-large · 3072 Dimension",
    "3", "RETRIEVE", "Scope Filter 선적용\nFTS·Identifier·Vector를 RRF로 결합",
    "원본 Repository를 OpenAI File·Vector Store에 업로드하지 않습니다.",
  ],
  [
    "Parser부터 활성화까지 구현 계약을 코드로 고정했습니다", "04",
    "Parser", "TREE_SITTER_V1 · 13 Parser · 8 Parsed / 26 Fallback",
    "Chunk", "24 KiB · stable UUIDv5 · 160 / 20 line · 64 records",
    "Embedding", "OPENAI_EMBEDDING_V1 · 3-large · 3072 · Batch 64",
    "Retrieval", "FTS 20 · Identifier 20 · Vector 30 · RRF k=60",
    "Activation", "34 / 34 · atomic switch · previous ACTIVE withdrawn",
    "Failure", "APPROVED return · partial activation 0",
    "Contract", "21 OpenAPI · 12 Migration files · 87 tests",
    "모든 구현 계약과 저장소 검증이 통과했습니다.",
  ],
  [
    "전체 파일이 성공한 뒤에만 새 인덱스가 활성화됩니다", "05",
    "SCAN", "승인 Commit\n34 Eligible",
    "PARSE", "8 Parsed\n26 Fallback",
    "EMBED", "64 Vectors\n1 Batch",
    "ACTIVATE", "34 = 34\nACTIVE",
    "파일 수 불일치나 Provider 오류가 있으면 부분 인덱스를 공개하지 않습니다.",
  ],
  [
    "실패는 APPROVED로 복귀하고 재실행은 새 멱등키로 통제됩니다", "06",
    "FAIL", "DB Adapter\n오류 감지",
    "REVERT", "Source를\nAPPROVED 복귀",
    "FIX", "계약 Alias·\nJSONB 수정",
    "RETRY", "새 Job·\n새 멱등키",
    "ACTIVE", "34 / 34\n원자 활성화",
    "초기 2건 실패에서도 활성 Chunk 0건을 유지해 Fail-closed 정책을 검증했습니다.",
  ],
  [
    "소스·Provider·삭제 경계가 원문과 비밀정보를 보호합니다", "07",
    "SOURCE SAFETY", "Checkout·Hook·Build·Test 0\nVerified Blob Text만 Parser 입력\nD0·1 MiB·Secret 검사 상속",
    "PROVIDER SAFETY", "Runtime Secret File 전용\nPrompt·Response 원문 감사 저장 금지\n이번 Canary 외부 호출 0",
    "DELETE SAFETY", "WITHDRAW 즉시 검색 제외\nChunk·Vector·Symbol·Relation 삭제\nLedger에 수량·상태만 기록",
    "실 API Canary는 운영자가 Key를 주입한 뒤 동일 Adapter 경로에서 별도로 수행합니다.",
  ],
  [
    "배포·재시작·삭제까지 시험 서버에서 검증했습니다", "08",
    "Gateway", "0.3.0 · Healthy · Image d767e5…fdd3e",
    "Schema", "19 Table · Issue #43 Column 8 · pgvector ready",
    "Parser", "13 Linux Parser prefetched · Read-only Image",
    "Index", "GENIE 34 / 34 · 64 Chunk · 64 Embedding",
    "Retrieve", "Top 10 · master@3e3c5c · Path / Line Citation",
    "Deletion", "격리 DB: 64 / 64 / 15 / 45 삭제 · 잔여 0",
    "Isolation", "기존 Activepieces 6 Container 모두 Healthy",
    "DB·Code·Image ID 백업 후 AI Gateway Compose 범위만 갱신했습니다.",
  ],
  [
    "활성 인덱스는 작고 정확해 exact cosine을 유지합니다", "09",
    "64", "CHUNKS", "34 File · 15 Symbol · 45 Relation",
    "64", "EMBEDDINGS", "3072 Dimension · 1 Mock Batch",
    "950", "GiB AVAILABLE", "Root ext4 사용률 2%",
    "14 GiB used", "1,005 GiB root",
    "50,000 Active Chunk 도달 전까지 HNSW는 비활성 · 동일 Golden Set으로 전환 판단",
  ],
  [
    "NEXT · ISSUE #44",
    "검색 근거가 준비됐습니다.\n이제 답변 생성과 보류 판정을 구현합니다.",
    "완료 1  ·  Parser·Chunk·Embedding·RRF Retrieval",
    "완료 2  ·  GENIE 34 Files·삭제 Drill·재시작 영속성",
    "다음  ·  OpenAI Responses·Structured Output·Citation 검증",
    "실 OpenAI Embedding Canary는 운영 API Key 주입 승인 후 별도 증적화",
  ],
];

const notes = [
  "[Sources]\n- TechFlow Issue #43 repository implementation and test server canary, 2026-08-05",
  "[Sources]\n- PostgreSQL active GENIE index metrics and isolated deletion drill, 2026-08-05",
  "[Sources]\n- https://developers.openai.com/api/reference/resources/embeddings/methods/create\n- https://developers.openai.com/api/docs/models/text-embedding-3-large\n- TechFlow ADR-0009 and Issue #43 implementation",
  "[Sources]\n- services/ai-gateway/app/chunking.py\n- services/ai-gateway/app/embedding.py\n- services/ai-gateway/app/indexing.py\n- services/ai-gateway/migrations/0005_parser_embedding_retrieval_up.sql",
  "[Sources]\n- services/ai-gateway/app/postgres_store.py\n- Test server GENIE ingestion job metrics, 2026-08-05",
  "[Sources]\n- Test server failed and successful ingestion job evidence, 2026-08-05",
  "[Sources]\n- docs/decisions/techflow-parser-embedding-retrieval.json\n- docs/adr/0009-openai-runtime-integration.md",
  "[Sources]\n- Test server health, schema, parser, index, deletion, and Activepieces checks, 2026-08-05",
  "[Sources]\n- Test server df, active index counts, and HNSW decision gate, 2026-08-05",
  "[Sources]\n- docs/plans/issue-20-rag-poc-design.md\n- GitHub Issue #44 scope",
];

async function writeBlob(target, blob) {
  await fs.writeFile(target, new Uint8Array(await blob.arrayBuffer()));
}

const deck = await PresentationFile.importPptx(await FileBlob.load(starter));
const inspection = await deck.inspect({ kind: "slide,textbox", include: "id,slide,text", maxChars: 100000 });
const groups = Array.from({ length: deck.slides.items.length }, () => []);
for (const line of inspection.ndjson.split(/\r?\n/)) {
  if (!line.trim()) continue;
  const record = JSON.parse(line);
  if (record.kind === "textbox") groups[record.slide - 1].push(record);
}

for (let slideIndex = 0; slideIndex < deck.slides.items.length; slideIndex += 1) {
  if (groups[slideIndex].length !== copy[slideIndex].length) {
    throw new Error(`Slide ${slideIndex + 1} textbox mismatch: ${groups[slideIndex].length} vs ${copy[slideIndex].length}`);
  }
  for (let index = 0; index < groups[slideIndex].length; index += 1) {
    const record = groups[slideIndex][index];
    const shape = deck.resolve(record.id);
    shape.text = copy[slideIndex][index];
  }
  deck.slides.items[slideIndex].speakerNotes.textFrame.setText(notes[slideIndex]);
  deck.slides.items[slideIndex].speakerNotes.setVisible(true);
}

await fs.mkdir(path.dirname(finalPptx), { recursive: true });
await fs.mkdir(renderDir, { recursive: true });
await fs.mkdir(layoutDir, { recursive: true });
for (let index = 0; index < deck.slides.items.length; index += 1) {
  const slide = deck.slides.items[index];
  await writeBlob(`${renderDir}/slide-${String(index + 1).padStart(2, "0")}.png`, await deck.export({ slide, format: "png", scale: 2 }));
  const layout = await deck.export({ slide, format: "layout" });
  await fs.writeFile(`${layoutDir}/slide-${String(index + 1).padStart(2, "0")}.json`, JSON.stringify(layout, null, 2), "utf8");
}
await writeBlob(`${root}/tmp/issue43-presentation/final-montage.webp`, await deck.export({ format: "webp", montage: true, scale: 1 }));
const pptx = await PresentationFile.exportPptx(deck);
await pptx.save(finalPptx);
const finalInspection = await deck.inspect({ kind: "slide,textbox,notes", maxChars: 100000 });
await fs.writeFile(`${root}/tmp/issue43-presentation/final-inspect.ndjson`, finalInspection.ndjson, "utf8");
console.log(JSON.stringify({ finalPptx, slides: deck.slides.items.length, textboxes: groups.reduce((sum, items) => sum + items.length, 0) }));
