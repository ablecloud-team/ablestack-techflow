import fs from "node:fs/promises";
import path from "node:path";
import { Presentation, PresentationFile } from "@oai/artifact-tool";
import { buildSlide10 } from "./grid/slide-10.mjs";
import { buildSlide17 } from "./grid/slide-17.mjs";
import { buildSlide19 } from "./grid/slide-19.mjs";
import { buildSlide26 } from "./grid/slide-26.mjs";

const ROOT = path.resolve(process.argv[2] ?? process.cwd());
const OUT_DIR = path.join(ROOT, "output", "presentation");
const QA_DIR = path.join(ROOT, "tmp", "artifacts", "issue-22", "qa");
const PPTX = path.join(OUT_DIR, "techflow-chat-community-approval.pptx");
const FONT = "Malgun Gothic";

function textToken(value, fontSize = "24px", bold = false, color = "#000000") {
  return { runs: [{ run: value, textStyle: { fontSize, typeface: FONT, bold, color } }] };
}

function bodyToken(title, body) {
  const heading = textToken(title, "24px", true);
  heading.spaceAfter = 800;
  heading.paragraphStyle = { lineSpacingPercent: 110000 };
  const content = textToken(body, "18px");
  content.spaceAfter = 800;
  content.paragraphStyle = { lineSpacingPercent: 114000 };
  return { titleHere: heading, loremIpsumDolorSitAmetConsecteturAdipiscing: content };
}

function notes(slide, sources) {
  slide.speakerNotes.textFrame.setText(`[Sources]\n${sources.map((source) => `- ${source}`).join("\n")}`);
  slide.speakerNotes.setVisible(true);
}

const deck = Presentation.create({ slideSize: { width: 1280, height: 720 } });

{
  const slide = buildSlide26(deck, {
    title: textToken("ABLESTACK TECHFLOW · ISSUE #22", "24px", true, "#4B5563"),
    title2: textToken("Community 승인을\nChat 하나로", "68px", true),
    title3: {
      loremIpsumDetails: textToken("알림 · 상세 · 승인", "22px", true),
      loremIpsumDetails2: textToken("수정 · 반려 · 이력", "22px"),
      loremIpsumDetails3: textToken("2026-08-12", "22px"),
    },
  });
  notes(slide, ["docs/reports/issue-22-chat-community-approval-validation.md", "docs/plans/issue-22-chat-community-approval-design.md"]);
}

{
  const slide = buildSlide17(deck, {
    title: textToken("검토 UI는 Chat, 정책과 상태는 AI Gateway가 소유합니다", "36px", true),
    label1: textToken("01 · 알림", "20px", true),
    label2: textToken("02 · 검토", "20px", true),
    label3: textToken("03 · 실행", "20px", true),
    body1: bodyToken("새 초안", "질문·Citation·링크와\n검토 버튼을 담당자에게 전송"),
    body2: bodyToken("Chat 명령", "대기·상세·승인·수정·\n반려·이력을 한 대화에서 처리"),
    body3: bodyToken("Activepieces", "현재 Version 결정만 실행\n승인된 답변만 Flarum 게시"),
    footer1: textToken("2", "13px"),
  });
  notes(slide, ["docs/plans/issue-22-chat-community-approval-design.md#2", "docs/runbooks/chat-community-approval.md#6"]);
}

{
  const slide = buildSlide10(deck, {
    title: textToken("승인 권한과 재처리 안전성을 Gateway 경계에서 강제했습니다", "36px", true),
    body1: textToken("Bot Token과 Chat 사용자 허용목록을 모두 통과한 담당자만 Case를 조작합니다.", "25px", true),
    body2: {
      loremIpsumDolorSitAmetConsecteturAdipiscing: textToken("Chat user_id와 username을 연결하고 reviewer를 chat:<username>으로 감사 기록합니다.\n\n현재 draftVersion만 승인하며 같은 목표 상태·버전의 재요청은 기존 결과를 반환합니다.", "19px"),
      loremIpsumDolorSitAmetConsecteturAdipiscing2: textToken("기존 github-chat-v1은 FROZEN 상태로 유지합니다.", "19px", true, "#1D4ED8"),
    },
    label1: textToken("Token 상수 시간 비교", "23px", true),
    label2: textToken("Reviewer allowlist", "23px", true),
    label3: textToken("Draft Version 검사", "23px", true),
    label4: textToken("결정 멱등성", "23px", true),
    label5: textToken("감사 이력", "23px", true),
    footer1: textToken("3", "13px"),
  });
  notes(slide, ["services/ai-gateway/app/chat_assist.py", "services/ai-gateway/app/main.py", "deploy/compose/activepieces/protected-services.json"]);
}

{
  const slide = buildSlide19(deck, {
    title: textToken("실제 서버와 Chat에서 운영 Gate를 통과했습니다", "36px", true),
    body1: {
      topic: textToken("검증 기준선", "20px", true),
      loremIpsumDolorSitAmetConsecteturAdipiscing: textToken("승인·수정·반려 E2E, 회귀 테스트, DB Schema와 외부 위조 요청 차단을 함께 확인했습니다.", "20px"),
    },
    stat1: textToken("3/3", "52px", true, "#2563EB"),
    stat2: textToken("152/152", "48px", true, "#15803D"),
    stat3: textToken("403", "52px", true, "#B91C1C"),
    body2: textToken("승인·수정·반려\nE2E 통과", "20px", true),
    body3: textToken("배포 이미지\n회귀 테스트", "20px", true),
    body4: textToken("위조 Chat 요청\n차단", "20px", true),
    footer1: textToken("4", "13px"),
  });
  notes(slide, ["docs/reports/issue-22-chat-community-approval-validation.md#5", "docs/reports/issue-22-chat-community-approval-validation.md#6"]);
}

{
  const slide = buildSlide10(deck, {
    title: textToken("세 가지 담당자 판단을 유효한 신규 Discussion으로 검증했습니다", "36px", true),
    body1: textToken("삭제된 #143을 성공 사례에서 제외하고 #145~#147로 다시 시험했습니다.", "25px", true),
    body2: {
      loremIpsumDolorSitAmetConsecteturAdipiscing: textToken("#145는 ANSWERED 초안을 버튼 승인해 Post #320으로 게시했습니다.\n\n#146은 ABSTAINED 초안을 추가 자료 요청 답변으로 수정해 Post #321로 게시했습니다.\n\n#147은 근거 없는 단정 요청을 사유와 함께 반려해 게시하지 않았습니다.", "19px"),
      loremIpsumDolorSitAmetConsecteturAdipiscing2: textToken("Chat 이력에서 네 Case의 최종 상태와 Reviewer를 확인했습니다.", "19px", true, "#1D4ED8"),
    },
    label1: textToken("#145 · PUBLISHED", "22px", true),
    label2: textToken("#146 · EDITED", "22px", true),
    label3: textToken("#147 · REJECTED", "22px", true),
    label4: textToken("#143 · DELETED", "22px", true),
    label5: textToken("대기 0건", "22px", true),
    footer1: textToken("5", "13px"),
  });
  notes(slide, ["https://community.ablecloud.io/d/145", "https://community.ablecloud.io/d/146", "https://community.ablecloud.io/d/147"]);
}

{
  const slide = buildSlide17(deck, {
    title: textToken("배포·장애·롤백 절차를 같은 완료 자산으로 고정했습니다", "36px", true),
    label1: textToken("BACKUP", "20px", true),
    label2: textToken("RECOVERY", "20px", true),
    label3: textToken("ROLLBACK", "20px", true),
    body1: bodyToken("사전 복구점", "DB·Compose·Ingress·\nImage·Source SHA-256 검증"),
    body2: bodyToken("장애 분리", "알림 실패는 대기 목록 복구\n삭제 원본은 반려 정리"),
    body3: bodyToken("최소 변경", "Chat Route와 Gateway만 복구\nGitHub Chat 서비스는 제외"),
    footer1: textToken("6", "13px"),
  });
  notes(slide, ["docs/runbooks/chat-community-approval.md#4", "docs/runbooks/chat-community-approval.md#8"]);
}

{
  const slide = buildSlide26(deck, {
    title: textToken("ISSUE #22 · PHASE 1", "24px", true, "#4B5563"),
    title2: textToken("Chat 승인 경로는\n실사용 준비 완료", "64px", true),
    title3: {
      loremIpsumDetails: textToken("다음: 일반 기술 질문 수신", "22px", true),
      loremIpsumDetails2: textToken("RAG 자동 응답", "22px"),
      loremIpsumDetails3: textToken("담당자 전환·피드백", "22px"),
    },
  });
  notes(slide, ["docs/reports/issue-22-chat-community-approval-validation.md#9", "https://github.com/ablecloud-team/ablestack-techflow/issues/22"]);
}

async function writeBlob(target, blob) {
  await fs.writeFile(target, new Uint8Array(await blob.arrayBuffer()));
}

await fs.mkdir(OUT_DIR, { recursive: true });
await fs.mkdir(path.join(QA_DIR, "renders"), { recursive: true });
await fs.mkdir(path.join(QA_DIR, "layouts"), { recursive: true });

for (const [index, slide] of deck.slides.items.entries()) {
  const stem = `slide-${String(index + 1).padStart(2, "0")}`;
  await writeBlob(path.join(QA_DIR, "renders", `${stem}.png`), await deck.export({ slide, format: "png", scale: 2 }));
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(path.join(QA_DIR, "layouts", `${stem}.json`), await layout.text(), "utf8");
}

await writeBlob(path.join(QA_DIR, "montage.webp"), await deck.export({ format: "webp", montage: true, scale: 1 }));
const inspection = await deck.inspect({ kind: "slide,textbox,shape,notes", maxChars: 100000 });
await fs.writeFile(path.join(QA_DIR, "inspect.ndjson"), inspection.ndjson, "utf8");
const pptx = await PresentationFile.exportPptx(deck);
await pptx.save(PPTX);
console.log(JSON.stringify({ pptx: PPTX, slides: deck.slides.items.length, qa: QA_DIR }));
