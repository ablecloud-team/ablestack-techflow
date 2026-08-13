import fs from "node:fs/promises";
import path from "node:path";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const root = path.resolve(process.argv[2] ?? process.cwd()).replaceAll("\\", "/");
const evidence = JSON.parse(await fs.readFile(`${root}/docs/evidence/issue-71/flarum-1.8.18-validation.json`, "utf8"));
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
  addText(slide, "Flarum 1.8.18\n업데이트 검증", 42, 150, 650, 188, 58, true);
  addText(slide, "반복 롤백과 Community·TechFlow 회귀를\n운영 적용 전에 검증했습니다.", 42, 390, 650, 84, 24, false, C.gray);
  addRect(slide, 790, 44, 448, 586, C.pale, C.blue);
  addText(slide, "조건부\nGO", 836, 154, 350, 154, 64, true, C.green);
  addRule(slide, 836, 342, 350, C.blue, 2);
  addText(slide, "운영 서버 변경 없음\n명시적 승인 후 배포", 836, 382, 350, 96, 24, true);
  addText(slide, "2026-08-14", 42, 592, 420, 30, 18, false, C.gray);
  notes(slide, ["docs/reports/issue-71-flarum-1.8.18-validation.md", "docs/evidence/issue-71/flarum-1.8.18-validation.json"]);
}

// 2. Metrics - Codex Grid slide-19 hierarchy.
{
  const slide = deck.slides.add(); chrome(slide, "최종 패키지 집합으로 두 번 같은 결과를 얻었습니다", 2);
  addText(slide, "업데이트뿐 아니라 데이터와 첨부를 기준선으로 되돌리는 과정까지 반복했습니다.", 42, 178, 1120, 40, 21, false, C.gray);
  metric(slide, 42, "2/2", "업데이트·롤백", "validated-cycle-01과 03 모두 통과", C.green);
  metric(slide, 453, "216", "TechFlow 테스트", "AI 답변·Chat·대화·KB 계약 통과", C.green);
  metric(slide, 864, "0", "한글 내부 키", "Forum과 Admin에서 노출 없음", C.green);
  notes(slide, ["docs/evidence/issue-71/flarum-1.8.18-validation.json#repeatable_cycles", "docs/reports/issue-71-flarum-1.8.18-validation.md#기능과-회귀-시험"]);
}

// 3. Timeline - Codex Grid slide-17 hierarchy.
{
  const slide = deck.slides.add(); chrome(slide, "한 사이클은 복원 가능성까지 끝내야 완료입니다", 3);
  addRule(slide, 64, 352, 1128, C.ink, 2);
  const steps = [
    [70, "01", "동일 시점 백업", "앱·설정·DB·업로드를\n한 변경 ID로 묶음"],
    [350, "02", "사전 계산", "Composer 호환성과\n변경 패키지를 고정"],
    [630, "03", "업데이트·검증", "Migration·한글 Asset·\nCommunity 기능 확인"],
    [910, "04", "복원·정합성", "업무 DB와 첨부 해시를\n기준선과 비교"],
  ];
  for (const [x, n, label, body] of steps) {
    slide.shapes.add({ geometry: "ellipse", position: { left: x, top: 334, width: 36, height: 36 }, fill: C.ink, line: { style: "solid", fill: C.ink, width: 1 } });
    addText(slide, n, x - 6, 264, 130, 28, 18, true, C.blue);
    addText(slide, label, x - 6, 398, 240, 38, 23, true);
    addText(slide, body, x - 6, 458, 240, 74, 18, false, C.gray);
  }
  addText(slide, "실패하면 운영 전환 없이 같은 창에서 1.8.10 기준선으로 복원합니다.", 64, 596, 1120, 34, 22, true);
  notes(slide, ["docs/runbooks/flarum-1.8.18-upgrade-rollback.md#WSL-반복-리허설"]);
}

// 4. Integrity evidence.
{
  const slide = deck.slides.add(); chrome(slide, "게시물과 첨부는 업데이트와 롤백 뒤에도 그대로였습니다", 4);
  const headers = ["지표", "기준선", "1.8.18", "롤백"];
  const xs = [42, 430, 700, 970], ws = [388, 270, 270, 268];
  headers.forEach((value, i) => { addRect(slide, xs[i], 184, ws[i], 48, C.ink, C.ink); addText(slide, value, xs[i] + 12, 196, ws[i] - 24, 24, 16, true, C.white); });
  const rows = [
    ["사용자", "39", "39", "39"], ["토론", "117", "117", "117"], ["게시물", "305", "305", "305"],
    ["첨부파일", "114", "114", "114"], ["첨부 용량", "25,939,695 B", "동일", "동일"], ["첨부 SHA-256", "19cdf526…a97c", "동일", "동일"],
  ];
  rows.forEach((row, index) => row.forEach((value, i) => { const top = 232 + index * 58; addRect(slide, xs[i], top, ws[i], 58, index % 2 ? C.white : "#F7F9FC", C.line); addText(slide, value, xs[i] + 12, top + 16, ws[i] - 24, 26, 17, i === 0); }));
  addText(slide, "만료 access_tokens는 정상 정리 대상이며, 모든 업무 테이블은 복원 전후 동일했습니다.", 42, 604, 1120, 36, 19, true, C.gray);
  notes(slide, ["docs/evidence/issue-71/flarum-1.8.18-validation.json#integrity"]);
}

// 5. Functional validation with two-column narrative.
{
  const slide = deck.slides.add(); chrome(slide, "사용자 기능과 TechFlow 자동화 경계를 함께 확인했습니다", 5);
  addText(slide, "실제 사용자 시나리오", 42, 184, 540, 40, 25, true, C.blue);
  addText(slide, "격리한 외부 연동", 678, 184, 540, 40, 25, true, C.blue);
  addRect(slide, 42, 244, 560, 330, "#F7F9FC", C.line);
  addRect(slide, 678, 244, 560, 330, "#F7F9FC", C.line);
  addText(slide, "로그인\n토론 생성과 답글\n검색\n이미지 첨부\nBest Answer 지정", 74, 274, 480, 250, 23, true);
  addText(slide, "Webhook · OAuth · Pusher · Scout\n\n스테이징 발송은 끄고\n216개 TechFlow 테스트로\nAI 답변·Chat·대화·KB 계약 확인", 710, 274, 480, 250, 22, true);
  addText(slide, "로그·압축 업로드는 #72에서 확장하고 별도 E2E를 수행합니다.", 42, 610, 1196, 32, 20, true, C.gray);
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
  addText(slide, "운영 규칙: SMTP 유지 · Sendmail 전환 금지 · Issue #74에서 교체 추적", 42, 566, 1196, 42, 22, true);
  notes(slide, ["docs/evidence/issue-71/flarum-1.8.18-validation.json#security", "docs/reports/issue-71-flarum-1.8.18-validation.md#보안-검토"]);
}

// 7. Decision close.
{
  const slide = deck.slides.add(); slide.background.fill = C.white;
  addText(slide, "ISSUE #71", 42, 40, 300, 30, 16, true, C.gray);
  addText(slide, "운영 승인 전까지\n변경하지 않습니다", 42, 164, 760, 176, 58, true);
  addRule(slide, 42, 392, 1196, C.blue, 3);
  addText(slide, "승인 후: 백업 → 업데이트 → Community·TechFlow E2E → Go 또는 즉시 롤백", 42, 438, 1160, 54, 24, true);
  addText(slide, "WSL은 1.8.18 검증 상태로 유지 · 다음 #72 대용량 업로드 · #73 UI · #74 운영 강화", 42, 554, 1160, 58, 20, false, C.gray);
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
