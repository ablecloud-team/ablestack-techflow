import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

const runtimeModules = process.env.RUNTIME_NODE_MODULES;
if (!runtimeModules) throw new Error("RUNTIME_NODE_MODULES is required");
const artifactToolUrl = pathToFileURL(path.join(runtimeModules, "@oai", "artifact-tool", "dist", "artifact_tool.mjs")).href;
const { Presentation, PresentationFile } = await import(artifactToolUrl);

const ROOT = process.env.TECHFLOW_ROOT;
if (!ROOT) throw new Error("TECHFLOW_ROOT is required");
const renderDir = path.join(ROOT, "tmp", "issue74-presentation", "renders");
const output = path.join(ROOT, "output", "presentation", "techflow-community-operations.pptx");
await fs.mkdir(renderDir, { recursive: true });
await fs.mkdir(path.dirname(output), { recursive: true });

const deck = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const C = {
  ink: "#15253E", gray: "#52647D", canvas: "#F3F7FC", line: "#D5E1F1",
  pale: "#EAF2FF", blue: "#155EEF", cyan: "#25B8E8", green: "#078248",
  paleGreen: "#EAFAF2", yellow: "#FFF6DF", amber: "#9A6700", red: "#B42318",
  white: "#FFFFFF", dark: "#243B64",
};
const FONT = "Malgun Gothic";

function box(slide, name, left, top, width, height, fill=C.white, line=C.line, geometry="roundRect") {
  return slide.shapes.add({ geometry, name, position: { left, top, width, height }, fill, line: { style: "solid", fill: line, width: 1 }, borderRadius: "rounded-xl" });
}
function text(slide, name, value, left, top, width, height, size=24, bold=false, color=C.ink, align="left") {
  const item = slide.shapes.add({ geometry: "textbox", name, position: { left, top, width, height }, fill: "none", line: { style: "solid", fill: "none", width: 0 } });
  item.text = value;
  item.text.style = { fontSize: size, bold, color, typeface: FONT, alignment: align };
  return item;
}
function title(slide, value, number) {
  text(slide, `title-${number}`, value, 48, 36, 1120, 68, 40, true);
  text(slide, `page-${number}`, String(number).padStart(2, "0"), 1170, 658, 62, 24, 16, false, C.gray, "right");
}
function metric(slide, name, value, label, left, top, width, accent=C.blue) {
  box(slide, `${name}-box`, left, top, width, 190, C.white, C.line);
  box(slide, `${name}-rule`, left, top, 8, 190, accent, accent, "rect");
  text(slide, `${name}-value`, value, left + 30, top + 38, width - 58, 76, 48, true, accent, "center");
  text(slide, `${name}-label`, label, left + 30, top + 124, width - 58, 40, 21, false, C.gray, "center");
}
function notes(slide) {
  slide.speakerNotes.textFrame.setText("[Sources]\n- docs/reports/issue-74-community-operations-validation.md\n- docs/evidence/issue-74/community-operations-validation.json\n- docs/adr/0010-community-backup-observability-security.md\n- docs/runbooks/community-backup-monitor-security.md\n- https://symfony.com/cve-2026-45068");
}

{
  const s = deck.slides.add(); s.background.fill = C.white;
  text(s, "cover-kicker", "ABLESTACK TECHFLOW · ISSUE #74", 48, 42, 640, 34, 20, true, C.gray);
  text(s, "cover-title", "Community 운영을\n복구 가능한 상태로", 48, 150, 650, 190, 64, true);
  text(s, "cover-subtitle", "암호화 백업 · 5분 관측 · Chat 경보 · 보안 강화", 48, 382, 690, 64, 27, false, C.gray);
  box(s, "cover-orbit", 800, 104, 352, 352, C.pale, C.blue);
  text(s, "cover-go", "GO", 834, 198, 284, 100, 80, true, C.blue, "center");
  text(s, "cover-rto", "운영 Snapshot 복원 9초", 824, 326, 304, 50, 24, true, C.ink, "center");
  text(s, "cover-date", "2026.08.19 · Production validated", 48, 590, 720, 40, 21, false, C.gray);
  notes(s);
}
{
  const s = deck.slides.add(); s.background.fill = C.white; title(s, "수동 백업을 자동 복구 체계로 바꿨습니다", 2);
  const rows = [
    ["백업", "수동 시점별 폴더", "매일 03:20 · 무결성 자동 검증"],
    ["보호", "일부 평문 Archive", "OpenPGP · 운영 서버 공개키만"],
    ["복원", "절차 증적 없음", "WSL 별도 App·DB 전체 복원"],
    ["관측", "서비스별 수동 확인", "5분 상태·Metric·Chat 전이 경보"],
    ["보안", "기본 Header·권한", "Rate Limit·TLS·0640/0600"],
  ];
  text(s, "before-head", "기준선", 350, 132, 250, 40, 23, true, C.gray, "center");
  text(s, "after-head", "적용 후", 770, 132, 300, 40, 23, true, C.blue, "center");
  rows.forEach((row, index) => {
    const y = 190 + index * 84;
    text(s, `row-label-${index}`, row[0], 68, y + 18, 180, 38, 23, true, C.ink);
    text(s, `row-before-${index}`, row[1], 270, y + 18, 360, 38, 21, false, C.gray, "center");
    text(s, `row-arrow-${index}`, "→", 644, y + 14, 64, 46, 28, true, C.blue, "center");
    text(s, `row-after-${index}`, row[2], 720, y + 18, 490, 38, 21, true, C.ink, "center");
    box(s, `row-rule-${index}`, 68, y + 69, 1142, 1, C.line, C.line, "rect");
  });
  notes(s);
}
{
  const s = deck.slides.add(); s.background.fill = C.white; title(s, "DB와 업로드를 한 시점으로 묶어 암호화합니다", 3);
  const steps = [
    ["01", "쓰기 정지", "PHP-FPM"], ["02", "DB Dump", "MariaDB"], ["03", "App Snapshot", "설정·업로드"],
    ["04", "즉시 재개", "PHP-FPM"], ["05", "공개키 암호화", "OpenPGP"], ["06", "Manifest 검증", "SHA-256"],
  ];
  steps.forEach((step, index) => {
    const left = 52 + index * 202;
    if (index < 5) text(s, `step-arrow-${index}`, "→", left + 164, 306, 38, 44, 28, true, C.gray, "center");
    box(s, `step-${index}`, left, 222, 164, 214, index >= 4 ? C.pale : C.canvas, index >= 4 ? C.blue : C.line);
    text(s, `step-no-${index}`, step[0], left + 18, 244, 128, 34, 18, true, index >= 4 ? C.blue : C.gray, "center");
    text(s, `step-title-${index}`, step[1], left + 14, 296, 136, 48, 23, true, C.ink, "center");
    text(s, `step-detail-${index}`, step[2], left + 14, 364, 136, 42, 18, false, C.gray, "center");
  });
  box(s, "backup-policy", 182, 500, 916, 96, C.paleGreen, "#86D2AA");
  text(s, "backup-policy-text", "운영 30일 보존 · RPO 24시간+10분 · 실패한 .partial은 자동 제거", 218, 528, 844, 40, 24, true, C.green, "center");
  notes(s);
}
{
  const s = deck.slides.add(); s.background.fill = C.white; title(s, "복호화 열쇠와 백업을 다른 장애 영역에 둡니다", 4);
  box(s, "prod", 66, 182, 470, 324, C.canvas, C.line);
  text(s, "prod-title", "운영 Community", 100, 220, 402, 48, 30, true, C.ink, "center");
  text(s, "prod-copy", "암호화 Backup\n공개키\n30일 보존\n\n개인키 없음", 120, 296, 362, 172, 25, false, C.gray, "center");
  text(s, "vault-arrow", "암호화 Archive만  →", 532, 314, 218, 52, 23, true, C.blue, "center");
  box(s, "vault", 746, 182, 470, 324, C.pale, C.blue);
  text(s, "vault-title", "WSL 복구 Vault", 780, 220, 402, 48, 30, true, C.blue, "center");
  text(s, "vault-copy", "개인키·Passphrase\nroot 전용 0600\n별도 App·DB 복원\n\n운영 경로 기본 거부", 800, 296, 362, 172, 25, false, C.ink, "center");
  text(s, "vault-result", "단일 서버 침해만으로는 백업 원문을 열 수 없습니다", 90, 566, 1100, 46, 25, true, C.green, "center");
  notes(s);
}
{
  const s = deck.slides.add(); s.background.fill = C.white; title(s, "운영 Snapshot은 9초에 완전히 복원됐습니다", 5);
  metric(s, "rto", "9초", "App·DB 복원 RTO", 70, 166, 340, C.blue);
  metric(s, "tables", "32", "복원 Table", 470, 166, 340, C.green);
  metric(s, "files", "11,336", "복원 File", 870, 166, 340, C.cyan);
  const counts = [["사용자", "41 = 41"], ["토론", "121 = 121"], ["게시물", "325 = 325"], ["첨부", "115 = 115"]];
  counts.forEach((count, index) => {
    const left = 70 + index * 285;
    text(s, `count-name-${index}`, count[0], left, 438, 240, 34, 20, false, C.gray, "center");
    text(s, `count-value-${index}`, count[1], left, 486, 240, 46, 27, true, C.ink, "center");
  });
  text(s, "restore-http", "격리 HTTP 200 · 0.947초 · 핵심 데이터 차이 0건", 100, 584, 1080, 44, 25, true, C.green, "center");
  notes(s);
}
{
  const s = deck.slides.add(); s.background.fill = C.white; title(s, "5분마다 서비스부터 AI 연동까지 한 번에 봅니다", 6);
  const labels = ["Nginx", "PHP-FPM", "MariaDB", "Community\nHTTP", "AI 연동\nHTTP", "Disk·inode", "Backup", "Mail Driver"];
  labels.forEach((label, index) => {
    const col = index % 4, row = Math.floor(index / 4);
    const left = 76 + col * 292, top = 166 + row * 178;
    box(s, `signal-${index}`, left, top, 248, 134, index === 7 ? C.paleGreen : C.pale, index === 7 ? "#86D2AA" : C.line);
    text(s, `signal-mark-${index}`, "✓", left + 20, top + 32, 44, 44, 30, true, index === 7 ? C.green : C.blue, "center");
    text(s, `signal-label-${index}`, label, left + 70, top + 32, 158, 64, 22, true, C.ink, "center");
  });
  text(s, "signal-result", "Production 3/3 Active · HTTP 200/200/200 · Disk 1% · Alert 0", 70, 566, 1140, 52, 25, true, C.green, "center");
  notes(s);
}
{
  const s = deck.slides.add(); s.background.fill = C.white; title(s, "Chat은 상태가 바뀔 때만 알립니다", 7);
  const states = [
    ["장애", "AI Health 실패", C.red, "Chat 1회"],
    ["동일 장애", "같은 Fingerprint", C.amber, "1시간 억제"],
    ["복구", "전체 점검 정상", C.green, "Chat 1회"],
  ];
  states.forEach((state, index) => {
    const left = 94 + index * 390;
    if (index < 2) text(s, `alert-arrow-${index}`, "→", left + 322, 308, 68, 46, 32, true, C.gray, "center");
    box(s, `alert-${index}`, left, 192, 322, 282, C.white, state[2]);
    box(s, `alert-top-${index}`, left, 192, 322, 12, state[2], state[2], "rect");
    text(s, `alert-title-${index}`, state[0], left + 30, 242, 262, 48, 30, true, state[2], "center");
    text(s, `alert-detail-${index}`, state[1], left + 30, 316, 262, 42, 22, false, C.ink, "center");
    text(s, `alert-result-${index}`, state[3], left + 30, 394, 262, 38, 22, true, state[2], "center");
  });
  text(s, "chat-proof", "Mock 전이 2회 · 운영 시험 전송 HTTP 200 · Payload는 text와 url만", 80, 552, 1120, 52, 24, true, C.blue, "center");
  notes(s);
}
{
  const s = deck.slides.add(); s.background.fill = C.white; title(s, "권한·TLS·Rate Limit·로그 기준을 함께 통과했습니다", 8);
  const leftItems = [
    ["5개", "외부 보안 Header"], ["27/40", "Auth 요청 HTTP 429"], ["0건", "World-writable File"],
  ];
  leftItems.forEach((item, index) => metric(s, `security-${index}`, item[0], item[1], 54 + index * 302, 170, 260, index === 2 ? C.green : C.blue));
  box(s, "security-list", 952, 170, 280, 360, C.canvas, C.line);
  text(s, "security-list-title", "운영 확인", 980, 198, 224, 38, 24, true, C.ink, "center");
  text(s, "security-list-copy", "TLS 1.0 차단\nTLS 1.2 허용\nconfig.php 0640\nOps Secret 0600\nLogrotate PASS\nSecret Scan 0", 988, 260, 208, 228, 21, false, C.gray, "center");
  text(s, "security-foot", "자동 보안 갱신 Timer enabled / active", 80, 580, 1100, 42, 24, true, C.green, "center");
  notes(s);
}
{
  const s = deck.slides.add(); s.background.fill = C.white; title(s, "남은 Mailer 위험은 실행 경로를 닫아 관리합니다", 9);
  box(s, "risk", 74, 174, 450, 332, C.yellow, "#E4B955");
  text(s, "risk-title", "잔여 위험", 108, 212, 382, 46, 29, true, C.amber, "center");
  text(s, "risk-copy", "Symfony Mailer\nCVE-2026-45068\n\nSendmailTransport의\n명령행 인자 처리", 118, 284, 362, 176, 24, false, C.ink, "center");
  text(s, "risk-arrow", "→", 538, 312, 72, 50, 38, true, C.blue, "center");
  box(s, "control", 626, 174, 580, 332, C.paleGreen, "#86D2AA");
  text(s, "control-title", "현재 통제", 660, 212, 512, 46, 29, true, C.green, "center");
  text(s, "control-copy", "운영 Mail Driver = smtp\n5분마다 강제 확인\n변경 시 Critical Chat 경보\n\n상위 Flarum 호환 시 안전 버전 교체", 674, 284, 484, 176, 24, false, C.ink, "center");
  text(s, "risk-foot", "위험을 없앴다고 주장하지 않고, 사용하지 않는 취약 경로를 지속 감시합니다", 80, 566, 1120, 50, 23, true, C.blue, "center");
  notes(s);
}
{
  const s = deck.slides.add(); s.background.fill = C.white;
  text(s, "close-kicker", "ISSUE #74 · COMPLETE", 48, 42, 520, 34, 20, true, C.gray);
  text(s, "close-title", "Community 운영 판정은\nGO입니다", 48, 150, 720, 186, 64, true);
  text(s, "close-proof", "자동 Backup · 9초 Restore · 5분 Monitor · Chat 200\nTheme·한글 Locale·TLS·Rate Limit·권한·로그 검증 완료", 48, 398, 790, 96, 26, false, C.gray);
  box(s, "close-status", 900, 166, 310, 310, C.pale, C.blue);
  text(s, "close-go", "GO", 934, 242, 242, 94, 68, true, C.blue, "center");
  text(s, "close-data", "핵심 데이터 차이 0", 932, 356, 246, 56, 22, true, C.ink, "center");
  text(s, "close-next", "다음: 승인된 외부 Backup Vault 연결 · 분기 전체 복원 훈련", 48, 582, 1120, 48, 24, true, C.green);
  notes(s);
}

for (const [index, slide] of deck.slides.items.entries()) {
  const stem = `slide-${String(index + 1).padStart(2, "0")}`;
  const png = await deck.export({ slide, format: "png", scale: 1 });
  await fs.writeFile(path.join(renderDir, `${stem}.png`), new Uint8Array(await png.arrayBuffer()));
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(path.join(renderDir, `${stem}.layout.json`), await layout.text());
}
const montage = await deck.export({ format: "webp", montage: true, scale: 1 });
await fs.writeFile(path.join(renderDir, "montage.webp"), new Uint8Array(await montage.arrayBuffer()));
const pptx = await PresentationFile.exportPptx(deck);
await pptx.save(output);
console.log(output);
