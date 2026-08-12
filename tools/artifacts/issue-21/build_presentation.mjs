import fs from "node:fs/promises";
import path from "node:path";
import { Presentation, PresentationFile } from "@oai/artifact-tool";
import { buildSlide01 } from "./grid/slide-01.mjs";
import { buildSlide05 } from "./grid/slide-05.mjs";
import { buildSlide17 } from "./grid/slide-17.mjs";
import { buildSlide19 } from "./grid/slide-19.mjs";
import { buildSlide26 } from "./grid/slide-26.mjs";

const ROOT = path.resolve(process.argv[2] ?? process.cwd());
const OUT_DIR = path.join(ROOT, "output", "presentation");
const QA_DIR = path.join(ROOT, "tmp", "artifacts", "issue-21", "qa");
const PPTX = path.join(OUT_DIR, "techflow-community-assist.pptx");
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
  return {
    titleHere: heading,
    loremIpsumDolorSitAmetConsecteturAdipiscing: content,
  };
}

function notes(slide, sources) {
  slide.speakerNotes.textFrame.setText(`[Sources]\n${sources.map((source) => `- ${source}`).join("\n")}`);
  slide.speakerNotes.setVisible(true);
}

const deck = Presentation.create({ slideSize: { width: 1280, height: 720 } });

{
  const slide = buildSlide01(deck, {
    title: textToken("ABLESTACK TECHFLOW · ISSUE #21", "24px", true, "#4B5563"),
    title2: textToken("Community 질문 답변\nFlow 구현 완료", "68px", true),
    title3: textToken("새 질문 수집 · 근거 기반 초안 · 담당자 승인 · 멱등 게시\n2026-08-12", "24px"),
  });
  notes(slide, ["docs/reports/issue-21-community-assist-validation.md", "docs/plans/issue-21-community-assist-design.md"]);
}

{
  const slide = buildSlide17(deck, {
    title: textToken("정책과 상태는 Gateway가, 순서 실행은 Activepieces가 담당합니다", "36px", true),
    label1: textToken("01 · 수집", "20px", true),
    label2: textToken("02 · 생성", "20px", true),
    label3: textToken("03 · 검토", "20px", true),
    body1: bodyToken("Flarum Poller", "새 미답변 질문만 정규화\n첨부는 Artifact ID로 변환"),
    body2: bodyToken("RAG + Responses", "ABLESTACK 문서·코드 검색\nCitation 포함 초안 생성"),
    body3: bodyToken("승인 후 게시", "현재 Draft Version만 승인\nAI-Assistant로 1회 게시"),
    footer1: textToken("2", "13px"),
  });
  notes(slide, ["docs/plans/issue-21-community-assist-design.md#3", "deploy/compose/activepieces/flows/community-assist-v1.json"]);
}

{
  const slide = buildSlide19(deck, {
    title: textToken("실제 시험은 생성·게시·회귀 세 Gate를 모두 통과했습니다", "36px", true),
    body1: {
      topic: textToken("실측 결과", "20px", true),
      loremIpsumDolorSitAmetConsecteturAdipiscing: textToken("답변 가능한 질문과 근거 부족 질문을 모두 시험해 자동 게시 안전성을 확인했습니다.", "20px"),
    },
    stat1: textToken("3", "52px", true, "#2563EB"),
    stat2: textToken("1,513", "52px", true, "#2563EB"),
    stat3: textToken("129/129", "48px", true, "#15803D"),
    body2: textToken("Citation\n승인 답변 근거", "20px", true),
    body3: textToken("Draft 문자\nVersion 1", "20px", true),
    body4: textToken("회귀 테스트\n전체 통과", "20px", true),
    footer1: textToken("3", "13px"),
  });
  notes(slide, ["docs/reports/issue-21-community-assist-validation.md#8", "services/ai-gateway/tests"]);
}

{
  const slide = buildSlide05(deck, {
    title: textToken("답변 가능 질문은 게시하고 근거 부족 질문은 안전하게 보류했습니다", "36px", true),
    body1: bodyToken("#142 · ANSWERED → PUBLISHED", "질문: Cube 네트워크 본딩의 목적은 무엇인가?\n\n처리량과 중복성을 설명하고 3개 Line Citation을 제시했습니다. dhslove 승인 후 Flarum Post #311로 게시됐습니다."),
    body2: bodyToken("#141 · ABSTAINED → REJECTED", "질문: VM 시작 실패 시 무엇을 확인해야 하는가?\n\n검색 결과는 있었지만 답변 생성 기준을 충족하지 못했습니다. 반려 후 댓글 수 1로 유지되어 AI 답변이 게시되지 않았습니다."),
    footer1: textToken("4", "13px"),
  });
  notes(slide, ["docs/reports/issue-21-community-assist-validation.md#82", "https://community.ablecloud.io/d/142/311"]);
}

{
  const slide = buildSlide05(deck, {
    title: textToken("승인 답변은 근거와 운영 선택 조건을 함께 제시했습니다", "36px", true),
    body1: bodyToken("핵심 답변", "여러 물리 인터페이스를 하나의 논리 인터페이스로 통합해 처리량을 높이고 링크 장애에 대비한 중복성을 제공합니다. 활성-백업 또는 트래픽 로드밸런싱을 구성할 수 있습니다."),
    body2: bodyToken("근거와 안전 장치", "ablestack-docs의 networking.md와 book-of-cell.md를 고정 Commit·Line으로 인용했습니다. 모드에 따라 스위치 링크 집계 설정이 필요할 수 있음을 함께 안내했습니다."),
    footer1: textToken("5", "13px"),
  });
  notes(slide, ["docs/reports/issue-21-community-assist-validation.md#83", "ablecloud-team/ablestack-docs@50d50ad6c8c548dc58db866ca28b4cbb43cc74d0"]);
}

{
  const slide = buildSlide17(deck, {
    title: textToken("시험망 장애 두 건을 운영 경계로 고정해 복구 가능성을 높였습니다", "36px", true),
    label1: textToken("ROUTE", "20px", true),
    label2: textToken("STATE", "20px", true),
    label3: textToken("REPLAY", "20px", true),
    body1: bodyToken("NAT hairpin 제거", "Flarum 내부 API와\n공개 HTTPS URL 분리"),
    body2: bodyToken("Volume 권한 고정", "Init Container가\nUID 10001·0700 적용"),
    body3: bodyToken("중복 게시 방지", "동일 승인 재처리에도\nPost #311·댓글 2 유지"),
    footer1: textToken("6", "13px"),
  });
  notes(slide, ["docs/reports/issue-21-community-assist-validation.md#9", "docs/runbooks/community-assist.md"]);
}

{
  const slide = buildSlide05(deck, {
    title: textToken("백업·Secret·보호 가드까지 같은 완료 기준으로 검증했습니다", "36px", true),
    body1: bodyToken("복구 자산", "Flarum DB·config·Nginx와 AI Gateway DB·Compose·Source·Image 정보를 사전 백업했습니다. SHA-256 검증을 완료했고 Down Migration은 명시적 승인 후에만 실행합니다."),
    body2: bodyToken("변경 차단 경계", "자격정보는 GitHub Secrets와 런타임 파일로만 사용했습니다. github-chat-v1은 FROZEN 상태와 Flow ID·Published Version을 그대로 유지했고 보호 가드가 통과했습니다."),
    footer1: textToken("7", "13px"),
  });
  notes(slide, ["docs/reports/issue-21-community-assist-validation.md#6", "deploy/compose/activepieces/protected-services.json"]);
}

{
  const slide = buildSlide26(deck, {
    title: textToken("ISSUE #21", "24px", true, "#4B5563"),
    title2: textToken("사내 실증을 시작할\n기준선이 준비됐습니다", "64px", true),
    title3: {
      loremIpsumDetails: textToken("다음: 4주 운영 관측", "22px", true),
      loremIpsumDetails2: textToken("승인·반려·편집률 측정", "22px"),
      loremIpsumDetails3: textToken("Source 보강 요구 수집", "22px"),
    },
  });
  notes(slide, ["docs/reports/issue-21-community-assist-validation.md#12", "GitHub Issue #21"]);
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
