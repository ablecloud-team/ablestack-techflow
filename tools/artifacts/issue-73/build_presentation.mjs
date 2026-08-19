import fs from "node:fs/promises";
import path from "node:path";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const ROOT = process.env.TECHFLOW_ROOT;
if (!ROOT) throw new Error("TECHFLOW_ROOT is required");
const renderDir = path.join(ROOT, "tmp", "issue73-presentation", "renders");
const output = path.join(ROOT, "output", "presentation", "techflow-community-ui-modernization.pptx");
const beforeImage = path.join(ROOT, "docs", "evidence", "issue-73", "screenshots", "before", "home-desktop.png");
const afterImage = path.join(ROOT, "docs", "evidence", "issue-73", "screenshots", "after", "home-desktop.png");
const actionImage = path.join(ROOT, "docs", "evidence", "issue-73", "screenshots", "after", "post-actions-mobile.png");
const modalImage = path.join(ROOT, "docs", "evidence", "issue-73", "screenshots", "after", "tag-selection-modal-desktop.png");
await fs.mkdir(renderDir, { recursive: true });
await fs.mkdir(path.dirname(output), { recursive: true });

const deck = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const C = {
  ink: "#15253E", gray: "#52647D", canvas: "#F3F7FC", line: "#D5E1F1",
  pale: "#EAF2FF", blue: "#155EEF", green: "#078248", paleGreen: "#EAFAF2",
  yellow: "#FFF6DF", amber: "#9A6700", white: "#FFFFFF", dark: "#243B64",
};
const FONT = "Malgun Gothic";

async function bytes(file) {
  const data = await fs.readFile(file);
  return data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength);
}
function box(slide, name, left, top, width, height, fill=C.white, line=C.line, radius="roundRect") {
  return slide.shapes.add({ geometry: radius, name, position: { left, top, width, height }, fill, line: { style: "solid", fill: line, width: 1 } });
}
function text(slide, name, value, left, top, width, height, size=24, bold=false, color=C.ink, align="left") {
  const item = slide.shapes.add({ geometry: "textbox", name, position: { left, top, width, height }, fill: "none", line: { style: "solid", fill: "none", width: 0 } });
  item.text = value;
  item.text.style = { fontSize: size, bold, color, typeface: FONT, alignment: align };
  return item;
}
function title(slide, value, number) {
  text(slide, `title-${number}`, value, 48, 36, 1110, 72, 40, true);
  text(slide, `page-${number}`, String(number).padStart(2, "0"), 1172, 660, 60, 24, 16, false, C.gray, "right");
}
function addImage(slide, name, blob, left, top, width, height, fit="contain") {
  return slide.images.add({ name, blob, contentType: "image/png", fit, position: { left, top, width, height }, geometry: "roundRect", borderRadius: "rounded-xl" });
}
function notes(slide) {
  slide.speakerNotes.textFrame.setText("[Sources]\n- docs/reports/issue-73-community-ui-validation.md\n- docs/evidence/issue-73/community-theme-validation.json\n- docs/plans/issue-73-community-ui-modernization.md\n- docs/runbooks/community-theme-rollout-rollback.md");
}

const before = await bytes(beforeImage);
const after = await bytes(afterImage);
const action = await bytes(actionImage);
const modal = await bytes(modalImage);

{
  const s = deck.slides.add(); s.background.fill = C.white;
  text(s, "cover-kicker", "ABLESTACK TECHFLOW · ISSUE #73", 48, 42, 560, 36, 20, true, C.gray);
  text(s, "cover-title", "Community\n인터페이스 현대화", 48, 168, 540, 180, 62, true);
  text(s, "cover-subtitle", "브랜드 테마 · 한글 UX · 반응형 · 안전한 롤백", 48, 390, 540, 78, 26, false, C.gray);
  box(s, "cover-image-frame", 650, 42, 582, 590, C.canvas, C.line);
  addImage(s, "cover-after", after, 676, 74, 530, 526, "contain");
  text(s, "cover-status", "CONDITIONAL GO", 48, 558, 360, 48, 24, true, C.blue);
  notes(s);
}
{
  const s = deck.slides.add(); s.background.fill = C.white; title(s, "기능은 그대로, 읽기 계층은 더 분명해졌습니다", 2);
  text(s, "before-label", "BEFORE", 48, 122, 540, 34, 20, true, C.gray);
  text(s, "after-label", "AFTER", 668, 122, 540, 34, 20, true, C.blue);
  addImage(s, "before-screen", before, 48, 166, 540, 338, "contain");
  addImage(s, "after-screen", after, 668, 166, 540, 338, "contain");
  text(s, "before-copy", "좁은 행 간격 · 약한 상태 구분 · 모바일 겹침", 48, 532, 540, 52, 22, false, C.gray, "center");
  text(s, "after-copy", "62px 단일 행 · 제목·태그·댓글 수 한 줄 · 240px 탐색", 668, 532, 540, 52, 19, true, C.ink, "center");
  notes(s);
}
{
  const s = deck.slides.add(); s.background.fill = C.white; title(s, "진행 답변과 선택된 해결 답변을 간결하게 구분합니다", 3);
  const states = [
    { y: 158, fill: C.white, line: C.line, label: "사용자 질문", detail: "증상과 첨부파일", color: C.ink },
    { y: 270, fill: C.pale, line: "#A8C5F2", label: "AI 기술지원", detail: "진행 중인 전문 엔지니어 답변", color: C.blue },
    { y: 382, fill: C.yellow, line: "#E4B955", label: "추가 확인 필요", detail: "로그·화면·환경 정보 요청", color: C.amber },
    { y: 494, fill: C.paleGreen, line: "#86D2AA", label: "해결된 답변", detail: "작은 배지 · 녹색 강조선 · 중복 작성자 정보 제거", color: C.green },
  ];
  states.forEach((state, index) => {
    box(s, `state-${index}`, 94, state.y, 1092, 86, state.fill, state.line);
    text(s, `state-label-${index}`, state.label, 130, state.y + 19, 320, 44, 26, true, state.color);
    text(s, `state-detail-${index}`, state.detail, 476, state.y + 21, 650, 40, 22, false, C.ink);
  });
  notes(s);
}
{
  const s = deck.slides.add(); s.background.fill = C.white; title(s, "본문 길이에 관계없이 버튼 간격을 하나로 맞췄습니다", 4);
  addImage(s, "mobile-actions", action, 52, 140, 260, 440, "contain");
  addImage(s, "tag-modal", modal, 346, 140, 842, 350, "contain");
  text(s, "action-caption", "카드-버튼 8px · 편차 0px", 42, 594, 280, 36, 19, true, C.blue, "center");
  box(s, "dialog-result", 346, 520, 842, 106, C.pale, C.blue);
  text(s, "dialog-result-main", "공통 Modal 규칙 · 부드러운 2px 포커스 · 직접 노출 영문 0건", 378, 540, 778, 38, 22, true, C.ink, "center");
  text(s, "dialog-result-sub", "주 태그를 선택하세요 · 확인 · 태그 필수 조건 무시", 378, 580, 778, 30, 19, false, C.blue, "center");
  notes(s);
}
{
  const s = deck.slides.add(); s.background.fill = C.white; title(s, "활성화와 롤백에도 콘텐츠는 그대로였습니다", 5);
  const labels = ["기준선\nDisabled", "활성화\nEnabled", "롤백\nDisabled", "최종\nEnabled"];
  labels.forEach((label, i) => {
    const left = 70 + i * 295;
    if (i < 3) text(s, `arrow-${i}`, "→", left + 232, 295, 58, 52, 32, true, C.gray, "center");
    box(s, `phase-${i}`, left, 236, 228, 164, i % 2 ? C.pale : C.canvas, i % 2 ? C.blue : C.line);
    text(s, `phase-label-${i}`, label, left + 20, 268, 188, 74, 26, true, i % 2 ? C.blue : C.ink, "center");
    text(s, `phase-http-${i}`, "HTTP 200", left + 20, 350, 188, 30, 18, false, C.gray, "center");
  });
  text(s, "integrity-count", "39 users · 117 discussions · 305 posts", 90, 478, 1100, 58, 32, true, C.ink, "center");
  text(s, "integrity-hash", "콘텐츠 SHA-256 동일 · 첨부 SHA-256 동일 · 정적 계약 8/8", 90, 550, 1100, 48, 24, false, C.green, "center");
  notes(s);
}
{
  const s = deck.slides.add(); s.background.fill = C.white; title(s, "Flarum Core를 건드리지 않아 롤백은 확장 하나로 끝납니다", 6);
  text(s, "flow-arrow-1", "→", 404, 286, 80, 50, 36, true, C.gray, "center");
  text(s, "flow-arrow-2", "→", 796, 286, 80, 50, 36, true, C.gray, "center");
  box(s, "flarum-core", 70, 218, 330, 190, C.canvas, C.line);
  box(s, "theme-extension", 480, 218, 312, 190, C.pale, C.blue);
  box(s, "community-ui", 872, 218, 330, 190, C.paleGreen, "#86D2AA");
  text(s, "flarum-core-title", "Flarum 1.8.18", 98, 266, 274, 48, 30, true, C.ink, "center");
  text(s, "flarum-core-copy", "라우팅 · 권한 · 검색 · 작성", 98, 326, 274, 34, 20, false, C.gray, "center");
  text(s, "theme-title", "ABLESTACK\nTheme", 506, 248, 260, 78, 29, true, C.blue, "center");
  text(s, "theme-copy", "LESS · 한글 Cache · 상태 표시", 506, 342, 260, 34, 18, false, C.gray, "center");
  text(s, "ui-title", "Community UI", 900, 266, 274, 48, 30, true, C.green, "center");
  text(s, "ui-copy", "Desktop · Mobile · Accessibility", 900, 326, 274, 34, 20, false, C.gray, "center");
  box(s, "rollback-strip", 250, 502, 780, 88, C.yellow, "#E4B955");
  text(s, "rollback-copy", "장애 시 extension:disable → 기본 Flarum UI 복귀", 282, 524, 716, 42, 26, true, C.amber, "center");
  notes(s);
}
{
  const s = deck.slides.add(); s.background.fill = C.white;
  text(s, "close-kicker", "ISSUE #73 · IMPLEMENTATION COMPLETE", 48, 42, 650, 36, 20, true, C.gray);
  text(s, "close-title", "운영 적용만\n승인하면 됩니다", 48, 168, 700, 180, 64, true);
  text(s, "close-detail", "WSL 전체 주기 PASS · 한글 원문 키·태그창 직접 영문 0건\nCore·Vendor·DB·운영 Community 변경 없음", 48, 422, 800, 92, 26, false, C.gray);
  box(s, "close-status", 900, 174, 310, 310, C.pale, C.blue);
  text(s, "close-go", "GO", 934, 242, 242, 94, 68, true, C.blue, "center");
  text(s, "close-condition", "운영 반영 승인 대기", 932, 356, 246, 56, 22, true, C.ink, "center");
  text(s, "close-next", "다음: 백업 → 테마 적용 → Desktop/Mobile Smoke → 해시 비교", 48, 584, 1120, 48, 23, true, C.green);
  notes(s);
}

for (const [index, slide] of deck.slides.items.entries()) {
  const blob = await deck.export({ slide, format: "png", scale: 1 });
  await fs.writeFile(path.join(renderDir, `slide-${String(index + 1).padStart(2, "0")}.png`), new Uint8Array(await blob.arrayBuffer()));
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(path.join(renderDir, `slide-${String(index + 1).padStart(2, "0")}.layout.json`), await layout.text());
}
const montage = await deck.export({ format: "webp", montage: true, scale: 1 });
await fs.writeFile(path.join(renderDir, "montage.webp"), new Uint8Array(await montage.arrayBuffer()));
const pptx = await PresentationFile.exportPptx(deck);
await pptx.save(output);
console.log(output);
