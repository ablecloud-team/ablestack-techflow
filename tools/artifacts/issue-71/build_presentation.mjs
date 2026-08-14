import fs from "node:fs/promises";
import path from "node:path";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const root = path.resolve(process.argv[2] ?? process.cwd()).replaceAll("\\", "/");
const evidence = JSON.parse(await fs.readFile(`${root}/docs/evidence/issue-71/flarum-1.8.18-validation.json`, "utf8"));
const production = evidence.production_rollout;
const final = production.final;
const outDir = `${root}/output/presentation`;
const qaDir = `${root}/tmp/issue71-presentation`;
const pptxPath = `${outDir}/techflow-flarum-1.8.18-upgrade.pptx`;
const deck = Presentation.create({ slideSize: { width: 1280, height: 720 } });

const C = { white: "#FFFFFF", ink: "#101010", gray: "#5B616B", panel: "#EDEDED", line: "#B8BCC4", blue: "#3D8DFF", pale: "#EAF5FB", green: "#117A4B", amber: "#A15C00", red: "#B42318" };
const FONT = "Malgun Gothic";

function addText(slide, value, left, top, width, height, size = 20, bold = false, color = C.ink, align = "left") {
  const shape = slide.shapes.add({ geometry: "textbox", position: { left, top, width, height }, fill: "none", line: { style: "solid", fill: "none", width: 0 } });
  shape.text = String(value);
  shape.text.style = { fontSize: size, bold, color, alignment: align, typeface: FONT, autoFit: "shrinkText" };
  return shape;
}

function addRect(slide, left, top, width, height, fill = C.panel, line = C.panel) {
  return slide.shapes.add({ geometry: "rect", position: { left, top, width, height }, fill, line: { style: "solid", fill: line, width: 1 } });
}

function addRule(slide, left, top, width, color = C.line, weight = 1) {
  slide.shapes.add({ geometry: "straightConnector1", position: { left, top, width, height: 0 }, fill: "none", line: { style: "solid", fill: color, width: weight } });
}

function chrome(slide, title, number) {
  slide.background.fill = C.white;
  addText(slide, "ABLESTACK TECHFLOW · ISSUE #71", 42, 28, 700, 28, 14, true, C.gray);
  addText(slide, title, 42, 66, 1196, 72, 39, true);
  addRule(slide, 42, 144, 1196);
  addText(slide, String(number).padStart(2, "0"), 1180, 668, 58, 22, 13, false, C.gray, "right");
}

function notes(slide, sources) {
  slide.speakerNotes.textFrame.setText(`[Sources]\n${sources.map((source) => `- ${source}`).join("\n")}`);
  slide.speakerNotes.setVisible(true);
}

function metric(slide, left, value, label, detail, color = C.blue) {
  addRect(slide, left, 330, 374, 278, C.panel);
  addText(slide, value, left + 30, 358, 314, 90, 52, true, color);
  addText(slide, label, left + 30, 462, 314, 34, 22, true);
  addText(slide, detail, left + 30, 518, 314, 64, 17, false, C.gray);
}

// 1. Cover - Codex Grid slide-08 inspired split field.
{
  const slide = deck.slides.add(); slide.background.fill = C.white;
  addText(slide, "ABLESTACK TECHFLOW", 42, 38, 520, 30, 16, true, C.gray);
  addText(slide, "Flarum 1.8.18\n운영 반영 완료", 42, 150, 650, 188, 58, true);
  addText(slide, "반복 롤백 검증을 거쳐 Community와\nTechFlow 통합 상태까지 확인했습니다.", 42, 390, 650, 84, 24, false, C.gray);
  addRect(slide, 790, 44, 448, 586, C.pale, C.blue);
  addText(slide, "GO\n완료", 836, 154, 350, 154, 64, true, C.green);
  addRule(slide, 836, 342, 350, C.blue, 2);
  addText(slide, "운영 1.8.18\n데이터 정합성 PASS", 836, 382, 350, 96, 24, true);
  addText(slide, "2026-08-14", 42, 592, 420, 30, 18, false, C.gray);
  notes(slide, ["docs/reports/issue-71-flarum-1.8.18-validation.md", "docs/evidence/issue-71/flarum-1.8.18-validation.json"]);
}

// 2. Metrics - Codex Grid slide-19 hierarchy.
{
  const slide = deck.slides.add(); chrome(slide, "운영 업데이트와 통합 검증을 모두 통과했습니다", 2);
  addText(slide, "스테이징 반복 검증에 이어 운영 데이터, 브라우저 화면과 자동화 서비스까지 확인했습니다.", 42, 178, 1120, 40, 21, false, C.gray);
  metric(slide, 42, "1.8.18", "운영 Flarum", "Nicknames 1.8.3 · SMTP · Debug Off", C.green);
  metric(slide, 453, "0", "데이터 차이", "39명 · 토론 120 · 게시물 320 · 첨부 115", C.green);
  metric(slide, 864, "PASS", "TechFlow 통합", "Poller 회복 · AI Gateway · Activepieces", C.green);
  notes(slide, ["docs/evidence/issue-71/flarum-1.8.18-validation.json#repeatable_cycles", "docs/reports/issue-71-flarum-1.8.18-validation.md#기능과-회귀-시험"]);
}

// 3. Timeline - Codex Grid slide-17 hierarchy.
{
  const slide = deck.slides.add(); chrome(slide, "첫 실행의 자동 롤백이 두 번째 성공을 안전하게 만들었습니다", 3);
  addRule(slide, 64, 352, 1128, C.ink, 2);
  const steps = [
    [70, "01", "첫 실행", "공개 URL 자체 점검이\nNAT loopback으로 시간 초과"],
    [350, "02", "자동 롤백", "1.8.10과 데이터 기준선을\n차이 없이 복원"],
    [630, "03", "점검 경로 보정", "127.0.0.1과 실제 Host·\nHTTPS 전달 헤더 사용"],
    [910, "04", "두 번째 성공", "1.8.18 유지·브라우저·\nTechFlow 통합 확인"],
  ];
  for (const [x, n, label, body] of steps) {
    slide.shapes.add({ geometry: "ellipse", position: { left: x, top: 334, width: 36, height: 36 }, fill: C.ink, line: { style: "solid", fill: C.ink, width: 1 } });
    addText(slide, n, x - 6, 264, 130, 28, 18, true, C.blue);
    addText(slide, label, x - 6, 398, 240, 38, 23, true);
    addText(slide, body, x - 6, 458, 240, 74, 18, false, C.gray);
  }
  addText(slide, "두 실행의 백업과 첫 실행의 빈 rollback.diff를 운영 증적으로 보존합니다.", 64, 596, 1120, 34, 22, true);
  notes(slide, ["docs/runbooks/flarum-1.8.18-upgrade-rollback.md#WSL-반복-리허설"]);
}

// 4. Integrity evidence.
{
  const slide = deck.slides.add(); chrome(slide, "운영 게시물과 첨부는 업데이트 전후 그대로입니다", 4);
  const headers = ["지표", "변경 전", "변경 후", "결과"];
  const xs = [42, 430, 700, 970], ws = [388, 270, 270, 268];
  headers.forEach((value, i) => { addRect(slide, xs[i], 184, ws[i], 48, C.ink, C.ink); addText(slide, value, xs[i] + 12, 196, ws[i] - 24, 24, 16, true, C.white); });
  const rows = [
    ["사용자", final.users, final.users, "일치"], ["토론", final.discussions, final.discussions, "일치"], ["게시물", final.posts, final.posts, "일치"],
    ["첨부파일", final.upload_files, final.upload_files, "일치"], ["첨부 용량", "26,060,120 B", "26,060,120 B", "일치"], ["첨부 SHA-256", "35cbac9f…ff50", "동일", "일치"],
  ];
  rows.forEach((row, index) => row.forEach((value, i) => { const top = 232 + index * 58; addRect(slide, xs[i], top, ws[i], 58, index % 2 ? C.white : "#F7F9FC", C.line); addText(slide, value, xs[i] + 12, top + 16, ws[i] - 24, 26, 17, i === 0); }));
  addText(slide, "성공 백업: /var/backups/techflow-flarum/issue-71-20260814T132424Z", 42, 604, 1120, 36, 19, true, C.gray);
  notes(slide, ["docs/evidence/issue-71/flarum-1.8.18-validation.json#integrity"]);
}

// 5. Functional validation with two-column narrative.
{
  const slide = deck.slides.add(); chrome(slide, "Community 화면과 TechFlow 자동화가 함께 회복됐습니다", 5);
  addText(slide, "운영 Community", 42, 184, 540, 40, 25, true, C.blue);
  addText(slide, "TechFlow 통합", 678, 184, 540, 40, 25, true, C.blue);
  addRect(slide, 42, 244, 560, 330, "#F7F9FC", C.line);
  addRect(slide, 678, 244, 560, 330, "#F7F9FC", C.line);
  addText(slide, "첫 화면 HTTP 200\n토론 상세 화면 정상\n한국어 내부 키 0건\n브라우저 콘솔 오류 0건\nFlarum CLI 1.8.18 확인", 74, 274, 480, 250, 23, true);
  addText(slide, "Community poller 자동 회복\n반복 poll failed=0\nAI Gateway healthy\nActivepieces healthy\nGitHub→Chat guard PASS", 710, 274, 480, 250, 22, true);
  addText(slide, "Admin 외부 403은 기존 접근 정책이며 공개 사용자 경로와 Flarum CLI로 운영 상태를 검증했습니다.", 42, 610, 1196, 32, 20, true, C.gray);
  notes(slide, ["docs/reports/issue-71-flarum-1.8.18-validation.md#기능과-회귀-시험", "docs/evidence/issue-71/flarum-1.8.18-validation.json#functional_validation"]);
}

// 6. Security decision.
{
  const slide = deck.slides.add(); chrome(slide, "운영은 SMTP 유지 조건에서만 Go입니다", 6);
  addRect(slide, 42, 194, 1196, 118, "#F1FAF5", C.green);
  addText(slide, "해결", 70, 222, 140, 30, 22, true, C.green);
  addText(slide, "Nicknames 1.8.3으로 CVE-2026-30913 제거", 228, 214, 950, 48, 28, true);
  addRect(slide, 42, 342, 1196, 170, "#FFF8ED", C.amber);
  addText(slide, "조건부 허용", 70, 372, 180, 30, 22, true, C.amber);
  addText(slide, "Symfony Mailer 6.1.11 · CVE-2026-45068", 270, 364, 900, 44, 27, true);
  addText(slide, "Sendmail 경로에 영향 · Flarum 1.8 의존성상 Mailer 6.4 설치 불가", 270, 424, 900, 34, 19, false, C.gray);
  addText(slide, "현재 운영 규칙: SMTP 유지 · Sendmail 전환 금지 · Issue #74에서 교체 추적", 42, 566, 1196, 42, 22, true);
  notes(slide, ["docs/evidence/issue-71/flarum-1.8.18-validation.json#security", "docs/reports/issue-71-flarum-1.8.18-validation.md#보안-검토"]);
}

// 7. Decision close.
{
  const slide = deck.slides.add(); slide.background.fill = C.white;
  addText(slide, "ISSUE #71", 42, 40, 300, 30, 16, true, C.gray);
  addText(slide, "Issue #71 운영 반영을\n완료했습니다", 42, 164, 760, 176, 58, true);
  addRule(slide, 42, 392, 1196, C.blue, 3);
  addText(slide, "백업 → 자동 롤백 검증 → 점검 보정 → 운영 업데이트 → Community·TechFlow 확인", 42, 438, 1160, 54, 24, true);
  addText(slide, "다음: #72 대용량 업로드 · #73 UI 현대화 · #74 백업·모니터링·잔여 보안", 42, 554, 1160, 58, 20, false, C.gray);
  notes(slide, ["docs/runbooks/flarum-1.8.18-upgrade-rollback.md#GoNo-Go-기준", "GitHub Issue #71"]);
}

async function writeBlob(target, blob) { await fs.writeFile(target, new Uint8Array(await blob.arrayBuffer())); }
await fs.mkdir(outDir, { recursive: true });
await fs.mkdir(`${qaDir}/renders`, { recursive: true });
await fs.mkdir(`${qaDir}/layouts`, { recursive: true });
await fs.writeFile(`${qaDir}/source-notes.txt`, "Repository sources only: Issue #71 evidence, report, and runbook.\n", "utf8");

for (let index = 0; index < deck.slides.items.length; index++) {
  const slide = deck.slides.items[index];
  const stem = `slide-${String(index + 1).padStart(2, "0")}`;
  await writeBlob(`${qaDir}/renders/${stem}.png`, await deck.export({ slide, format: "png", scale: 2 }));
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(`${qaDir}/layouts/${stem}.json`, await layout.text(), "utf8");
}
await writeBlob(`${qaDir}/montage.webp`, await deck.export({ format: "webp", montage: true, scale: 1 }));
const inspection = await deck.inspect({ kind: "slide,textbox,shape,notes", maxChars: 100000 });
await fs.writeFile(`${qaDir}/inspect.ndjson`, inspection.ndjson, "utf8");
const pptx = await PresentationFile.exportPptx(deck);
await pptx.save(pptxPath);
console.log(JSON.stringify({ pptxPath, slides: deck.slides.items.length, montage: `${qaDir}/montage.webp` }));
