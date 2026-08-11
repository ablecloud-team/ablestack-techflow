import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

const root = path.resolve(process.argv[2] ?? process.cwd()).replaceAll("\\", "/");
const artifactEntry = process.env.CODEX_ARTIFACT_TOOL_PATH ??
  `${root}/tmp/issue43-presentation/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs`;
const { Presentation, PresentationFile } = await import(pathToFileURL(artifactEntry));
const evaluation = JSON.parse(await fs.readFile(`${root}/output/issue-46-live-evaluation.json`, "utf8"));
const evidence = JSON.parse(await fs.readFile(`${root}/output/issue-46-server-evidence.json`, "utf8"));
const summary = evaluation.summary;
const records = evaluation.records;
const boundaryViolations = summary.securityBoundaryAnsweredViolations ?? summary.isolationAnsweredViolations;
const outDir = `${root}/output/presentation`;
const qaDir = `${root}/tmp/issue46-presentation`;
const pptxPath = `${outDir}/techflow-golden-set-quality-security-e2e.pptx`;

const deck = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const C = { white: "#FFFFFF", black: "#101010", gray: "#5B616B", panel: "#F2F2F2", line: "#B8BCC4", blue: "#3D8DFF", pale: "#DDF3FF", green: "#117A4B", red: "#B42318" };
const FONT = "Malgun Gothic";

function addText(slide, text, left, top, width, height, size = 20, bold = false, color = C.black, align = "left") {
  const shape = slide.shapes.add({ geometry: "textbox", position: { left, top, width, height }, fill: "none", line: { style: "solid", fill: "none", width: 0 } });
  shape.text = String(text);
  shape.text.style = { fontSize: size, bold, color, alignment: align, typeface: FONT, autoFit: "shrinkText" };
  return shape;
}

function addRect(slide, left, top, width, height, fill = C.panel, line = C.line) {
  return slide.shapes.add({ geometry: "rect", position: { left, top, width, height }, fill, line: { style: "solid", fill: line, width: 1 } });
}

function addRule(slide, left, top, width, color = C.line, weight = 1) {
  slide.shapes.add({ geometry: "straightConnector1", position: { left, top, width, height: 0 }, fill: "none", line: { style: "solid", fill: color, width: weight } });
}

function chrome(slide, title, number, kicker = "ABLESTACK TECHFLOW · ISSUE #46") {
  slide.background.fill = C.white;
  addText(slide, kicker, 42, 28, 700, 28, 14, true, C.gray);
  addText(slide, title, 42, 66, 1196, 72, 39, true);
  addRule(slide, 42, 144, 1196);
  addText(slide, String(number).padStart(2, "0"), 1180, 668, 58, 22, 13, false, C.gray, "right");
}

function setNotes(slide, sources) {
  slide.speakerNotes.textFrame.setText(`[Sources]\n${sources.map((item) => `- ${item}`).join("\n")}`);
  slide.speakerNotes.setVisible(true);
}

function metric(slide, left, value, label, note, color = C.blue) {
  addRect(slide, left, 330, 360, 270, C.panel, C.panel);
  addText(slide, value, left + 28, 360, 304, 86, 48, true, color);
  addText(slide, label, left + 28, 456, 304, 34, 20, true);
  addText(slide, note, left + 28, 506, 304, 70, 17, false, C.gray);
}

// 1. Sparse cover, Codex Grid cover silhouette.
{
  const slide = deck.slides.add(); slide.background.fill = C.white;
  addText(slide, "ABLESTACK TECHFLOW", 42, 36, 540, 32, 16, true, C.gray);
  addText(slide, "Golden Set·품질·보안·E2E\n검증 완료", 42, 154, 700, 210, 58, true);
  addRect(slide, 790, 44, 448, 586, C.pale, C.blue);
  addText(slide, "70", 836, 142, 350, 120, 84, true, C.blue);
  addText(slide, "실제 Golden Question", 836, 274, 350, 42, 24, true);
  addRule(slide, 836, 342, 350, C.blue, 2);
  addText(slide, "질문 · 기대 답변 · 실제 답변\nCitation · 자동 판정 · Codex 판정", 836, 374, 350, 122, 21, false);
  addText(slide, "AI Gateway 0.6.0 · Event Gateway 0.4.0\n2026-08-10", 42, 548, 650, 76, 20, false, C.gray);
  setNotes(slide, ["docs/reports/issue-46-golden-set-quality-security-e2e-validation.md", "output/issue-46-live-evaluation.json"]);
}

// 2. Metric-led result.
{
  const slide = deck.slides.add(); chrome(slide, "실제 Gateway 평가 결과가 완료 판단의 기준입니다", 2);
  addText(slide, "Reference Replay는 계약 검증용이며 아래 실측에 포함하지 않았습니다.", 42, 174, 1120, 38, 20, false, C.gray);
  metric(slide, 42, `${(summary.codexAcceptableAnswerRate * 100).toFixed(1)}%`, "Codex 수용 답변", `자동 엄격 답변 ${(summary.acceptableAnswerRate * 100).toFixed(1)}% · 불일치는 상세 보고`, summary.codexAcceptableAnswerRate >= .8 ? C.green : C.red);
  metric(slide, 460, `${(summary.correctAbstentionRate * 100).toFixed(0)}%`, "올바른 보류", "미지원·교차 범위 질문을 근거 없이 답하지 않음", summary.correctAbstentionRate >= .9 ? C.green : C.red);
  metric(slide, 878, `${boundaryViolations}`, "격리·보안 위반", "Branch·Repository·Test·Prompt·Secret·Allowlist 경계", boundaryViolations === 0 ? C.green : C.red);
  setNotes(slide, ["output/issue-46-live-evaluation.json#summary"]);
}

// 3. Process timeline.
{
  const slide = deck.slides.add(); chrome(slide, "검증은 승인된 소스에서 판정 자산까지 한 경로로 추적됩니다", 3);
  addRule(slide, 74, 350, 1110, C.black, 2);
  const steps = [
    [82, "1", "SCAN", "D0·Secret·PII·Prompt Injection 검역"],
    [365, "2", "INDEX", "Parser·Chunk·Embedding·원자적 활성화"],
    [648, "3", "QUERY", "고정 Source Profile 범위 Hybrid Retrieval"],
    [931, "4", "JUDGE", "자동 판정 + Codex 검토 + PDF/PPTX"],
  ];
  for (const [x, n, label, text] of steps) {
    slide.shapes.add({ geometry: "ellipse", position: { left: x, top: 332, width: 36, height: 36 }, fill: C.black, line: { style: "solid", fill: C.black, width: 1 } });
    addText(slide, n, x, 337, 36, 24, 16, true, C.white, "center");
    addText(slide, label, x - 4, 236, 220, 40, 23, true, C.blue);
    addText(slide, text, x - 4, 394, 230, 118, 18, false);
  }
  addText(slide, "Activepieces는 흐름을 실행하고, TechFlow AI Gateway가 정책·상태·검색·판정을 소유합니다.", 74, 574, 1080, 50, 22, true);
  setNotes(slide, ["docs/runbooks/golden-set-quality-security-e2e.md", "docs/decisions/techflow-golden-evaluation.json"]);
}

// 4. Source table-like evidence.
{
  const slide = deck.slides.add(); chrome(slide, "9개 Source Profile을 고정 Commit으로 색인했습니다", 4);
  const headers = ["PROFILE", "STATE", "FILES", "CHUNKS", "SYMBOLS", "RELATIONS"];
  const xs = [42, 350, 514, 654, 798, 950], ws = [300, 156, 132, 136, 144, 288];
  for (let i = 0; i < headers.length; i++) { addRect(slide, xs[i], 174, ws[i], 40, C.black, C.white); addText(slide, headers[i], xs[i] + 8, 184, ws[i] - 16, 20, 14, true, C.white); }
  evidence.sources.forEach((item, row) => {
    const top = 214 + row * 46, m = item.metrics ?? {}, values = [item.sourceProfileId, item.state, m.indexedFiles ?? 0, m.chunks ?? 0, m.symbols ?? 0, m.relations ?? 0];
    for (let i = 0; i < values.length; i++) { addRect(slide, xs[i], top, ws[i], 46, row % 2 ? C.white : "#F7F9FC"); addText(slide, values[i], xs[i] + 8, top + 11, ws[i] - 16, 23, 15, i === 0 || i === 1, i === 1 && values[i] === "ACTIVE" ? C.green : C.black); }
  });
  setNotes(slide, ["output/issue-46-server-evidence.json#sources"]);
}

// 5. Quality chart.
{
  const slide = deck.slides.add(); chrome(slide, "품질 Gate는 답변 정확성과 안전한 보류를 함께 봅니다", 5);
  slide.charts.add("bar", {
    position: { left: 42, top: 184, width: 720, height: 420 },
    categories: ["답변 수용", "보류 정확", "Citation", "Line 해석"],
    series: [{ name: "실측 %", values: [summary.acceptableAnswerRate * 100, summary.correctAbstentionRate * 100, summary.answeredCitationRate * 100, summary.codeLineResolvableRate * 100], fill: C.blue }],
    hasLegend: false, dataLabels: { showValue: true, position: "outEnd" },
    chartFill: C.white, chartLine: { style: "solid", fill: C.white, width: 0 },
    xAxis: { visible: true, textStyle: { typeface: FONT, fontSize: "15px", color: C.black } },
    yAxis: { visible: true, min: 0, max: 100, majorUnit: 20, majorGridlines: { style: "solid", fill: "#EDEDED", width: 1 }, textStyle: { typeface: FONT, fontSize: "13px", color: C.gray } },
  });
  addRect(slide, 810, 184, 428, 420, C.panel, C.panel);
  addText(slide, `${summary.providerP95Ms.toLocaleString()}ms`, 842, 230, 360, 68, 42, true, summary.providerP95Ms <= 12000 ? C.green : C.red);
  addText(slide, "Provider P95", 842, 304, 360, 36, 21, true);
  addRule(slide, 842, 366, 320);
  addText(slide, `기준 ≤ 12,000ms\n실 Provider 호출 ${summary.providerCalls}건\n격리·보안 위반 ${boundaryViolations}건`, 842, 398, 340, 138, 19, false);
  setNotes(slide, ["output/issue-46-live-evaluation.json#summary", "docs/decisions/techflow-golden-evaluation.json#qualityGates"]);
}

// 6. Bug/fix comparison.
{
  const slide = deck.slides.add(); chrome(slide, "실데이터 색인이 두 경계 결함을 드러냈고 모두 회귀 테스트로 고정했습니다", 6);
  addText(slide, "발견", 42, 184, 560, 40, 25, true, C.red); addText(slide, "개선", 678, 184, 560, 40, 25, true, C.green);
  addRect(slide, 42, 242, 560, 328, "#FFF4F2", C.red); addRect(slide, 678, 242, 560, 328, "#F1FAF5", C.green);
  addText(slide, "1  24KiB 입력이 OpenAI 8,192 token 초과\n\n2  공백 파일이 빈 임베딩 입력 생성\n\n3  관계명 1,024자·중복 Chunk 충돌\n\n4  Mock 기본값과 실증 배포 모드 혼선\n\n5  예외 원문이 로그에 포함될 가능성", 72, 250, 500, 310, 16, false);
  addText(slide, "1  7,936-byte 상한 + UTF-8 안전 분할\n\n2  공백 파일은 청크 0개로 안전 처리\n\n3  Hash 축약 + DB 계약 기준 중복 제거\n\n4  OpenAI Override + 무중단 REINDEX\n\n5  FK 인덱스 2개 + Batch 128/256KiB", 708, 250, 500, 310, 16, false);
  addText(slide, "Cockpit 203 files / QEMU 214 files 재색인 성공", 678, 590, 560, 36, 20, true, C.green);
  setNotes(slide, ["services/ai-gateway/app/chunking.py", "services/ai-gateway/app/postgres_store.py", "services/ai-gateway/tests/test_chunking.py"]);
}

// 7. Security boundaries.
{
  const slide = deck.slides.add(); chrome(slide, "원문 Q&A는 검토 자산에만 남고 운영 DB와 Flow에는 남지 않습니다", 7);
  const cols = [42, 446, 850], titles = ["SOURCE", "PROVIDER", "EVIDENCE"], bodies = [
    "D0 전용\n검역 제외 승인: dhslove\nSecret·PII·Prompt Injection 격리",
    "Responses store=false\nTool 0개\n승인된 모델 프로필만 허용",
    "DB: 상태·판정·Citation ID\nFlow: 원문 미보존\n보고서: D0 Q&A 전체 보존",
  ];
  for (let i = 0; i < 3; i++) { addRect(slide, cols[i], 220, 360, 330, C.panel, C.panel); addText(slide, titles[i], cols[i] + 26, 252, 308, 40, 24, true, C.blue); addText(slide, bodies[i], cols[i] + 26, 322, 308, 170, 20, false); }
  addText(slide, "ZDR은 사용하지 않으며 완료 Gate도 아닙니다.", 42, 592, 1196, 42, 22, true);
  setNotes(slide, ["docs/decisions/techflow-golden-evaluation.json#securityGates", "docs/runbooks/golden-set-quality-security-e2e.md"]);
}

// 8. Representative Q&A samples.
{
  const slide = deck.slides.add(); chrome(slide, "보고서에는 70개 질문과 실제 답변, Codex 판정을 모두 수록했습니다", 8);
  const samples = [records.find((r) => r.actualState === "ANSWERED"), records.find((r) => r.expectedState === "ABSTAINED"), records.find((r) => !r.automatedJudgment.passed)].filter(Boolean).slice(0, 3);
  const tops = [178, 330, 482];
  samples.forEach((r, i) => {
    addRect(slide, 42, tops[i], 1196, 126, i % 2 ? C.white : "#F7F9FC");
    addText(slide, `${r.caseKey} · ${r.reviewJudgment.verdict}`, 62, tops[i] + 16, 330, 28, 17, true, r.reviewJudgment.verdict === "ACCEPTED" ? C.green : C.red);
    addText(slide, r.question, 402, tops[i] + 14, 520, 48, 17, true);
    addText(slide, (r.actualAnswer ?? `보류: ${r.abstainReason ?? "근거 부족"}`).slice(0, 150), 402, tops[i] + 68, 760, 38, 15, false, C.gray);
    addText(slide, `${r.latencyMs.toLocaleString()}ms`, 1110, tops[i] + 18, 100, 24, 15, true, C.blue, "right");
  });
  setNotes(slide, ["output/issue-46-live-evaluation.json#records", "docs/reports/issue-46-golden-set-quality-security-e2e-validation.md#7"]);
}

// 9. Deployment and rollback.
{
  const slide = deck.slides.add(); chrome(slide, "배포·백업·롤백을 같은 서버에서 실제로 재현했습니다", 9);
  const stages = [
    ["BACKUP", "AI 82MB\nAP 83MB"], ["TEST", `${evidence.aiGatewayTests} + ${evidence.eventGatewayTests}\n회귀 테스트`],
    ["DEPLOY", "AI 0.6.0\nEvent 0.4.0"], ["ROLLBACK", "0.6→0.5→0.6\n0.4→0.3→0.4"],
  ];
  stages.forEach(([title, body], i) => { const x = 42 + i * 298; addRect(slide, x, 236, 260, 280, C.panel, C.panel); addText(slide, title, x + 24, 266, 212, 34, 21, true, C.blue); addText(slide, body, x + 24, 344, 212, 100, 25, true); if (i < 3) addText(slide, "→", x + 265, 346, 28, 44, 28, true); });
  addText(slide, `Root volume ${evidence.rootDisk ?? "1,005GiB / 2% used"} · 현재 이미지는 issue-46 / 0.4.0`, 42, 566, 1196, 38, 20, true);
  setNotes(slide, ["output/issue-46-server-evidence.json", "docs/runbooks/golden-set-quality-security-e2e.md#7"]);
}

// 10. Deliberate close.
{
  const slide = deck.slides.add(); slide.background.fill = C.white;
  addText(slide, "ISSUE #46", 42, 40, 300, 30, 16, true, C.gray);
  addText(slide, "완료 기준선이\n생겼습니다", 42, 174, 760, 200, 64, true);
  addRule(slide, 42, 422, 1196, C.blue, 3);
  addText(slide, "다음: 고객 기술지원 질문 회귀 평가 · 관측 대시보드 · 운영 승인 Gate", 42, 466, 1100, 54, 24, true);
  addText(slide, `실 평가 ${summary.totalCases}건 · 자동 통과 ${summary.passedCases}건 · Codex 수용 ${summary.codexAcceptedCases ?? 0}건 · 상세 Q&A는 보고서에 전체 수록`, 42, 570, 1100, 44, 20, false, C.gray);
  setNotes(slide, ["docs/reports/issue-46-golden-set-quality-security-e2e-validation.md", "GitHub Issue #46"]);
}

async function writeBlob(target, blob) { await fs.writeFile(target, new Uint8Array(await blob.arrayBuffer())); }
await fs.mkdir(outDir, { recursive: true }); await fs.mkdir(`${qaDir}/renders`, { recursive: true }); await fs.mkdir(`${qaDir}/layouts`, { recursive: true });
for (let index = 0; index < deck.slides.items.length; index++) {
  const slide = deck.slides.items[index]; const stem = `slide-${String(index + 1).padStart(2, "0")}`;
  await writeBlob(`${qaDir}/renders/${stem}.png`, await deck.export({ slide, format: "png", scale: 2 }));
  const layout = await slide.export({ format: "layout" }); await fs.writeFile(`${qaDir}/layouts/${stem}.json`, await layout.text(), "utf8");
}
await writeBlob(`${qaDir}/montage.webp`, await deck.export({ format: "webp", montage: true, scale: 1 }));
const inspection = await deck.inspect({ kind: "slide,textbox,chart,notes", maxChars: 100000 });
await fs.writeFile(`${qaDir}/inspect.ndjson`, inspection.ndjson, "utf8");
const pptx = await PresentationFile.exportPptx(deck); await pptx.save(pptxPath);
console.log(JSON.stringify({ pptxPath, slides: deck.slides.items.length, montage: `${qaDir}/montage.webp` }));
