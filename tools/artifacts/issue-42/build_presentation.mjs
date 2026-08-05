import fs from "node:fs/promises";
import path from "node:path";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const ROOT = path.resolve(process.argv[2]);
const OUTPUT = `${ROOT}/output/presentation/techflow-source-registry.pptx`;
const PREVIEW = `${ROOT}/tmp/issue-42-artifacts/preview`;
const LAYOUT = `${ROOT}/tmp/issue-42-artifacts/layout`;

const W = 1280;
const H = 720;
const BLACK = "#101010";
const GRAY = "#5B616B";
const LIGHT = "#EDEDED";
const RULE = "#B8BCC4";
const BLUE = "#3D8DFF";
const PALE = "#DDF3FF";
const GREEN = "#117A4B";
const RED = "#B42318";
const FONT = "Malgun Gothic";

const deck = Presentation.create({ slideSize: { width: W, height: H } });

function box(slide, x, y, w, h, fill = LIGHT, line = "none", radius = false) {
  return slide.shapes.add({
    geometry: radius ? "roundRect" : "rect",
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { style: "solid", fill: line, width: line === "none" ? 0 : 1 },
    ...(radius ? { borderRadius: "rounded-xl" } : {}),
  });
}

function text(slide, value, x, y, w, h, size = 24, color = BLACK, bold = false, align = "left") {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position: { left: x, top: y, width: w, height: h },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  shape.text = value;
  shape.text.style = { fontSize: size, color, bold, typeface: FONT, alignment: align };
  return shape;
}

function baseSlide(title, number) {
  const slide = deck.slides.add();
  slide.background.fill = "#FFFFFF";
  text(slide, title, 42, 34, 1150, 80, 38, BLACK, true);
  text(slide, String(number).padStart(2, "0"), 1182, 662, 56, 22, 13, GRAY, false, "right");
  return slide;
}

// Codex Grid slide-01 silhouette: sparse cover.
{
  const s = deck.slides.add();
  s.background.fill = "#FFFFFF";
  text(s, "ABLESTACK TECHFLOW · ISSUE #42", 42, 42, 640, 42, 24, BLACK, true);
  text(s, "Source Registry·검역·승인\n파이프라인 구현 완료", 42, 166, 1050, 236, 64, BLACK, true);
  text(s, "18 API · 18 Table · 9 Source Profile · Reviewer dhslove", 42, 505, 920, 48, 24, BLUE, true);
  text(s, "실제 승인 0건 · OpenAI 호출 0건 · 2026-08-05", 42, 571, 760, 44, 20, GRAY);
}

// Codex Grid slide-19 silhouette: three decisive metrics.
{
  const s = baseSlide("후보를 수집할 수 있지만 사람 승인 없이는 색인할 수 없습니다", 2);
  text(s, "#42는 실행 가능한 Source Gate를 구현하고 실제 Source 승인은 보류했습니다.", 42, 124, 1160, 50, 21, GRAY);
  const items = [
    ["9", "SOURCE PROFILES", "7개 저장소·Cloud 3개 Branch"],
    ["34", "ELIGIBLE FILES", "GENIE_MASTER Canary·제외 0"],
    ["0", "APPROVED / ACTIVE", "Provider Call도 0건"],
  ];
  items.forEach((item, i) => {
    const x = 42 + i * 411;
    box(s, x, 300, 374, 306, i === 2 ? PALE : LIGHT, "none", true);
    text(s, item[0], x + 30, 338, 310, 116, 76, i === 2 ? BLUE : BLACK, true);
    text(s, item[1], x + 30, 466, 310, 34, 20, BLACK, true);
    text(s, item[2], x + 30, 520, 310, 58, 17, GRAY);
  });
}

// Three-column process architecture inspired by Codex Grid slide-07.
{
  const s = baseSlide("Activepieces는 흐름을, AI Gateway는 정책과 상태를 소유합니다", 3);
  const cols = [
    ["1", "ACTIVEPIECES", "Branch Head 감지\n승인 요청·Job 호출\n재시도·알림"],
    ["2", "AI GATEWAY", "불변 Registry\n고정 Commit Fetch\n검역·멱등성·Gate"],
    ["3", "POSTGRESQL", "Version·Blob·File\nFinding·Approval·Job\n18개 Table"],
  ];
  cols.forEach((c, i) => {
    const x = 42 + i * 411;
    text(s, c[0], x, 218, 48, 48, 30, BLUE, true);
    box(s, x, 280, 374, 2, i === 1 ? BLUE : RULE);
    text(s, c[1], x, 318, 350, 36, 20, BLACK, true);
    text(s, c[2], x, 382, 350, 136, 25, BLACK);
  });
  text(s, "Parser·Chunk·Embeddings는 #43에서 이 Gate 뒤에 연결합니다.", 42, 612, 980, 30, 20, GREEN, true);
}

// Registry table evidence, aligned to Codex Grid slide-03/14.
{
  const s = baseSlide("7개 저장소를 9개 독립 Profile로 고정했습니다", 4);
  const rows = [
    ["SHARED_DOCS", "ablestack-docs", "master"],
    ["CLOUD_MAIN", "ablestack-cloud", "main"],
    ["CLOUD_DIPLO", "ablestack-cloud", "ablestack-diplo"],
    ["CLOUD_EUROPA", "ablestack-cloud", "ablestack-europa"],
    ["WALL_MAIN", "ablestack-wall", "main"],
    ["COCKPIT_DIPLO", "ablestack-cockpit-plugin", "ablestack-diplo"],
    ["GENIE_MASTER", "ablestack-genie", "master"],
    ["KICKSTART_MASTER", "ablestack-kickstart", "master"],
    ["QEMU_EXEC_TOOLS_MAIN", "ablestack-qemu-exec-tools", "main"],
  ];
  const x = [42, 420, 850];
  ["PROFILE", "REPOSITORY", "BRANCH"].forEach((v, i) => text(s, v, x[i] + 12, 166, [350, 402, 350][i], 28, 16, GRAY, true));
  rows.forEach((r, idx) => {
    const y = 205 + idx * 46;
    if (idx % 2 === 0) box(s, 42, y - 4, 1196, 42, "#F5F5F5");
    text(s, r[0], x[0] + 12, y, 350, 28, 15, BLACK, true);
    text(s, r[1], x[1] + 12, y, 402, 28, 15, BLACK);
    text(s, r[2], x[2] + 12, y, 350, 28, 15, BLACK);
  });
  text(s, "모든 Profile: D0 · 7일 삭제 SLA · 초기 Reviewer dhslove", 42, 628, 950, 30, 18, BLUE, true);
}

// Codex Grid slide-17 silhouette: lifecycle timeline.
{
  const s = baseSlide("새 Commit은 기존 승인을 상속하지 않고 전체 성공 후에만 활성화됩니다", 5);
  box(s, 76, 354, 1120, 2, BLACK);
  const steps = [
    ["REGISTERED", "Head 발견\nCommit 고정"],
    ["QUARANTINED", "정적 검역\n원문 실행 금지"],
    ["APPROVED", "dhslove\nCommit 확인"],
    ["INDEXING", "#43 Job\n부분 성공 금지"],
    ["ACTIVE", "원자 전환\n이전 버전 철회"],
  ];
  steps.forEach((step, i) => {
    const x = 76 + i * 244;
    box(s, x, 346, 18, 18, i < 3 ? BLUE : "#FFFFFF", BLACK, true);
    text(s, step[0], x, 270, 190, 32, 18, BLACK, true);
    text(s, step[1], x, 402, 190, 72, 18, GRAY);
  });
  text(s, "실패 → APPROVED 복귀  |  File 수 불일치 → ACTIVE 거부  |  Head 변경 → 새 Version", 76, 568, 1080, 36, 19, RED, true);
}

// Security controls as a restrained three-column evidence layout.
{
  const s = baseSlide("Fetcher는 소스를 읽지만 어떤 코드도 실행하지 않습니다", 6);
  const cols = [
    ["FETCH", "Bare Repository\n40자 Commit Pin\nls-tree·cat-file만\nHook·Checkout·LFS·Submodule 금지"],
    ["QUARANTINE", "D0 Allowlist\nBinary·Encoding·1 MiB\nSecret·PII·Injection\n제외 원문 미저장"],
    ["RUNTIME", "2 GiB tmpfs\nnoexec · nosuid · nodev\nUID 10001 · Read-only\nCapability ALL Drop"],
  ];
  cols.forEach((c, i) => {
    const x = 42 + i * 411;
    box(s, x, 190, 374, 390, i === 1 ? PALE : LIGHT);
    text(s, c[0], x + 26, 225, 320, 36, 22, i === 1 ? BLUE : BLACK, true);
    text(s, c[1], x + 26, 302, 320, 210, 22, BLACK);
  });
  text(s, "파일 목록 API는 Content를 반환하지 않고 Path·Hash·Decision·Rule만 제공합니다.", 42, 616, 1120, 32, 18, GREEN, true);
}

// Server evidence table.
{
  const s = baseSlide("시험 서버에서 배포·권한·차단 동작을 함께 검증했습니다", 7);
  const facts = [
    ["Gateway", "0.2.0 · Healthy · Image b0c3fd…dd4b"],
    ["Database", "18 Table · 9 Profile · vector + pg_trgm"],
    ["Canary", "GENIE 34 / 34 Eligible · Excluded 0 · Blocking 0"],
    ["Approval", "REGISTERED 8 · QUARANTINED 1 · APPROVED 0"],
    ["Fail closed", "미승인 Ingestion HTTP 409 · Query ABSTAINED"],
    ["Isolation", "기존 Activepieces 6 Container 모두 Healthy"],
  ];
  facts.forEach((f, i) => {
    const y = 160 + i * 75;
    text(s, f[0], 54, y, 220, 36, 19, i === 4 ? RED : BLACK, true);
    box(s, 286, y - 8, 2, 47, i === 4 ? RED : RULE);
    text(s, f[1], 316, y, 880, 40, 18, BLACK);
  });
  text(s, "백업 후 Migration·Canary를 수행했으며 Secret과 Source 원문은 산출물에 포함하지 않았습니다.", 54, 628, 1130, 30, 17, BLUE, true);
}

// Codex Grid slide-26 inspired closing: a concrete review decision.
{
  const s = deck.slides.add();
  s.background.fill = "#FFFFFF";
  text(s, "NEXT · ISSUE #43", 42, 42, 360, 42, 24, BLACK, true);
  text(s, "PR은 구현을 승인합니다.\nSource 승인은 별도입니다.", 42, 176, 1090, 190, 60, BLACK, true);
  text(s, "검토 1  ·  9개 Profile·Reviewer dhslove", 42, 462, 760, 34, 21, BLUE, true);
  text(s, "검토 2  ·  GENIE 34개 검역 결과", 42, 510, 760, 34, 21, BLUE, true);
  text(s, "다음  ·  Parser·Chunk·Embeddings·Hybrid Retrieval", 42, 558, 900, 34, 21, GREEN, true);
}

await fs.mkdir(path.dirname(OUTPUT), { recursive: true });
await fs.mkdir(PREVIEW, { recursive: true });
await fs.mkdir(LAYOUT, { recursive: true });
for (const [index, slide] of deck.slides.items.entries()) {
  const stem = `slide-${String(index + 1).padStart(2, "0")}`;
  const png = await deck.export({ slide, format: "png", scale: 1 });
  await fs.writeFile(`${PREVIEW}/${stem}.png`, new Uint8Array(await png.arrayBuffer()));
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(`${LAYOUT}/${stem}.json`, await layout.text());
}
const montage = await deck.export({ format: "webp", montage: true, scale: 1 });
await fs.writeFile(`${ROOT}/tmp/issue-42-artifacts/artifact-tool-montage.webp`, new Uint8Array(await montage.arrayBuffer()));
const inspect = await deck.inspect({ kind: "slide,textbox,shape", maxChars: 20000 });
await fs.writeFile(`${ROOT}/tmp/issue-42-artifacts/inspect.ndjson`, inspect.ndjson);
const pptx = await PresentationFile.exportPptx(deck);
await pptx.save(OUTPUT);
console.log(OUTPUT);
