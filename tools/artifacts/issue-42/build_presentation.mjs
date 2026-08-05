import fs from "node:fs/promises";
import path from "node:path";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const ROOT = path.resolve(process.argv[2]);
const OUTPUT = `${ROOT}/output/presentation/techflow-source-registry.pptx`;
const PREVIEW = `${ROOT}/tmp/issue-42-artifacts/preview`;
const LAYOUT = `${ROOT}/tmp/issue-42-artifacts/layout`;
const W = 1280, H = 720;
const BLACK = "#101010", GRAY = "#5B616B", LIGHT = "#EDEDED", RULE = "#B8BCC4";
const BLUE = "#3D8DFF", PALE = "#DDF3FF", GREEN = "#117A4B", RED = "#B42318";
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

// 01 · cover
{
  const s = deck.slides.add();
  s.background.fill = "#FFFFFF";
  text(s, "ABLESTACK TECHFLOW · ISSUE #42", 42, 42, 700, 42, 24, BLACK, true);
  text(s, "Source Registry·영속 미러·검역\n보완 구현 완료", 42, 156, 1080, 238, 62, BLACK, true);
  text(s, "19 API · 19 Table · 7 Persistent Mirrors · 9 Source Profiles", 42, 500, 1040, 48, 23, BLUE, true);
  text(s, "Root 1,005 GiB · 실제 승인 0건 · OpenAI 호출 0건 · 2026-08-05", 42, 568, 1080, 44, 20, GRAY);
}

// 02 · decision metrics
{
  const s = baseSlide("질의는 GitHub가 아닌 서버 로컬 자료를 사용합니다", 2);
  text(s, "발견 단계만 온라인이며 검역·향후 검색은 로컬 자산을 사용합니다.", 42, 124, 1160, 50, 21, GRAY);
  const items = [
    ["7", "PERSISTENT MIRRORS", "Repository별 Bare Mirror"],
    ["6h", "RECONCILIATION", "24시간 초과 시 STALE"],
    ["0", "ONLINE QUERY", "고정 Commit·승인 Index 사용"],
  ];
  items.forEach((item, i) => {
    const x = 42 + i * 411;
    box(s, x, 292, 374, 314, i === 2 ? PALE : LIGHT, "none", true);
    text(s, item[0], x + 30, 330, 310, 116, 72, i === 2 ? BLUE : BLACK, true);
    text(s, item[1], x + 30, 462, 310, 34, 19, BLACK, true);
    text(s, item[2], x + 30, 518, 310, 58, 17, GRAY);
  });
}

// 03 · architecture
{
  const s = baseSlide("GitHub Fetch와 로컬 스캔을 명확히 분리했습니다", 3);
  const cols = [
    ["1", "DISCOVERY", "GitHub HTTPS\n허용 Branch만 증분 Fetch\n6시간 Reconciler"],
    ["2", "PERSISTENT MIRROR", "7개 Bare Repository\nProfile별 Candidate Ref\nFile Lock·fsck·gc --auto"],
    ["3", "LOCAL DATA PATH", "ls-tree·cat-file Scan\nD0 Blob은 PostgreSQL\n#43 승인 Index 질의"],
  ];
  cols.forEach((c, i) => {
    const x = 42 + i * 411;
    text(s, c[0], x, 210, 48, 48, 30, BLUE, true);
    box(s, x, 272, 374, 2, i === 1 ? BLUE : RULE);
    text(s, c[1], x, 310, 350, 36, 20, BLACK, true);
    text(s, c[2], x, 374, 350, 156, 24, BLACK);
  });
  text(s, "GitHub 장애 시 신규 Head만 지연되고 기존 Mirror·Blob·승인 Index는 유지됩니다.", 42, 610, 1120, 32, 20, GREEN, true);
}

// 04 · registry table
{
  const s = baseSlide("7개 저장소를 9개 독립 Profile로 고정했습니다", 4);
  const rows = [
    ["SHARED_DOCS", "ablestack-docs", "master"], ["CLOUD_MAIN", "ablestack-cloud", "main"],
    ["CLOUD_DIPLO", "ablestack-cloud", "ablestack-diplo"], ["CLOUD_EUROPA", "ablestack-cloud", "ablestack-europa"],
    ["WALL_MAIN", "ablestack-wall", "main"], ["COCKPIT_DIPLO", "ablestack-cockpit-plugin", "ablestack-diplo"],
    ["GENIE_MASTER", "ablestack-genie", "master"], ["KICKSTART_MASTER", "ablestack-kickstart", "master"],
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
  text(s, "Cloud 3개 Profile은 한 Mirror 안에서 Branch·Candidate Ref를 분리합니다.", 42, 628, 1000, 30, 18, BLUE, true);
}

// 05 · synchronization timeline
{
  const s = baseSlide("6시간 동기화와 24시간 Stale 판정을 실제 운영합니다", 5);
  box(s, 92, 350, 1040, 2, BLACK);
  const steps = [
    ["START / 6h", "9개 Profile\n발견 API"],
    ["FETCH", "Branch → Mirror\n보호 Ref 생성"],
    ["SCAN", "로컬 Commit\n네트워크 없음"],
    ["STATE", "성공 HEALTHY\n24h 초과 STALE"],
  ];
  steps.forEach((step, i) => {
    const x = 92 + i * 320;
    box(s, x, 341, 20, 20, i < 3 ? BLUE : "#FFFFFF", BLACK, true);
    text(s, step[0], x, 262, 230, 34, 19, BLACK, true);
    text(s, step[1], x, 398, 230, 76, 18, GRAY);
  });
  text(s, "실패 → DEGRADED · 기존 데이터 유지  |  Push 즉시 갱신 → #45에서 Activepieces와 연결", 92, 565, 1080, 40, 19, RED, true);
}

// 06 · approval lifecycle
{
  const s = baseSlide("새 Commit은 기존 승인을 상속하지 않고 전체 성공 후에만 활성화됩니다", 6);
  box(s, 76, 354, 1120, 2, BLACK);
  const steps = [
    ["REGISTERED", "Head 발견\nCommit 고정"], ["QUARANTINED", "로컬 검역\n원문 실행 금지"],
    ["APPROVED", "dhslove\nCommit 확인"], ["INDEXING", "#43 Job\n부분 성공 금지"],
    ["ACTIVE", "원자 전환\n이전 버전 철회"],
  ];
  steps.forEach((step, i) => {
    const x = 76 + i * 244;
    box(s, x, 346, 18, 18, i < 3 ? BLUE : "#FFFFFF", BLACK, true);
    text(s, step[0], x, 270, 190, 32, 18, BLACK, true);
    text(s, step[1], x, 402, 190, 72, 18, GRAY);
  });
  text(s, "실패 → APPROVED 복귀  |  File 수 불일치 → ACTIVE 거부  |  실제 승인·활성 0건", 76, 568, 1080, 36, 19, RED, true);
}

// 07 · controls
{
  const s = baseSlide("Fetcher는 소스를 보존하지만 어떤 코드도 실행하지 않습니다", 7);
  const cols = [
    ["MIRROR", "Bare Repository\nCandidate Ref 보호\nRemote·Commit 검증\nRepository File Lock"],
    ["QUARANTINE", "D0 Allowlist\nBinary·Encoding·1 MiB\nSecret·PII·Injection\n제외 원문 미저장"],
    ["RUNTIME", "Named Volume 영속\nUID 10001 · Read-only Root\nCapability ALL Drop\nCheckout·Hook·Build 금지"],
  ];
  cols.forEach((c, i) => {
    const x = 42 + i * 411;
    box(s, x, 190, 374, 390, i === 1 ? PALE : LIGHT);
    text(s, c[0], x + 26, 225, 320, 36, 22, i === 1 ? BLUE : BLACK, true);
    text(s, c[1], x + 26, 302, 320, 220, 21, BLACK);
  });
  text(s, "File API는 Content를 반환하지 않고 Path·Hash·Decision·Rule만 제공합니다.", 42, 616, 1120, 32, 18, GREEN, true);
}

// 08 · deployment evidence
{
  const s = baseSlide("영속성·오프라인·차단 동작을 시험 서버에서 함께 검증했습니다", 8);
  const facts = [
    ["Gateway", "0.2.1 · Healthy · Image 36ee3c…b1b1c"],
    ["Database", "19 Table · 9 Profile · 7 Mirror State"],
    ["Reconciler", "9 / 9 성공 · 21,600초 · 7 HEALTHY"],
    ["Persistence", "7 Mirror · 906 MiB · Gateway 재시작 후 유지"],
    ["Offline", "network none · GENIE 34 / 34 Eligible"],
    ["Fail closed", "미승인 Ingestion HTTP 409 · Query ABSTAINED"],
    ["Isolation", "기존 Activepieces 6 Container 모두 Healthy"],
  ];
  facts.forEach((f, i) => {
    const y = 140 + i * 67;
    text(s, f[0], 54, y, 220, 34, 18, i === 5 ? RED : BLACK, true);
    box(s, 286, y - 7, 2, 44, i === 5 ? RED : RULE);
    text(s, f[1], 316, y, 880, 38, 18, BLACK);
  });
  text(s, "실제 Source 승인·활성화·OpenAI Provider Call은 모두 0건입니다.", 54, 626, 1080, 30, 18, BLUE, true);
}

// 09 · disk expansion
{
  const s = baseSlide("시험 서버 Root를 1TB까지 온라인 확장했습니다", 9);
  const items = [
    ["46.9", "GiB BEFORE", "sda3 · PV · Root LV"],
    ["1,020.9", "GiB AFTER", "sda3 · ubuntu-lv"],
    ["950", "GiB AVAILABLE", "Root ext4 사용률 2%"],
  ];
  items.forEach((item, i) => {
    const x = 42 + i * 411;
    box(s, x, 205, 374, 250, i === 2 ? PALE : LIGHT, "none", true);
    text(s, item[0], x + 26, 245, 320, 92, 56, i === 2 ? BLUE : BLACK, true);
    text(s, item[1], x + 26, 346, 320, 30, 18, BLACK, true);
    text(s, item[2], x + 26, 392, 320, 34, 16, GRAY);
  });
  box(s, 42, 516, 1196, 18, "#E8EDF4", "none", true);
  box(s, 42, 516, 24, 18, BLUE, "none", true);
  text(s, "14 GiB used", 42, 550, 220, 28, 16, BLACK, true);
  text(s, "1,005 GiB ext4", 1010, 550, 228, 28, 16, GRAY, true, "right");
  text(s, "Partition Table·VG Metadata 백업 후 growpart → pvresize → lvextend -r", 42, 612, 1120, 30, 18, GREEN, true);
}

// 10 · close
{
  const s = deck.slides.add();
  s.background.fill = "#FFFFFF";
  text(s, "NEXT · ISSUE #43", 42, 42, 360, 42, 24, BLACK, true);
  text(s, "로컬 Source 기반이 준비됐습니다.\n이제 검색 품질을 구현합니다.", 42, 168, 1120, 194, 58, BLACK, true);
  text(s, "검토 1  ·  7개 Mirror·6시간 주기·24시간 Stale", 42, 452, 920, 34, 21, BLUE, true);
  text(s, "검토 2  ·  Root 1,005 GiB·가용 950 GiB", 42, 500, 920, 34, 21, BLUE, true);
  text(s, "다음  ·  Parser·Chunk·Embeddings·Hybrid Retrieval", 42, 548, 980, 34, 21, GREEN, true);
  text(s, "Source 승인은 #43 Dry-run·원자 활성화 검증 뒤 별도로 수행", 42, 608, 980, 30, 18, GRAY);
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
const inspect = await deck.inspect({ kind: "slide,textbox,shape", maxChars: 30000 });
await fs.writeFile(`${ROOT}/tmp/issue-42-artifacts/inspect.ndjson`, inspect.ndjson);
const pptx = await PresentationFile.exportPptx(deck);
await pptx.save(OUTPUT);
console.log(OUTPUT);
