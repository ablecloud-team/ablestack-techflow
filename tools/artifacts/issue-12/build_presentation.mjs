import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const ROOT = process.argv[2]
  ? path.resolve(process.argv[2])
  : path.resolve(process.cwd(), "../../..");
const TMP = `${ROOT}/tmp/artifacts/issue-12`;
const STARTER = `${TMP}/template-starter.pptx`;
const OUTPUT = `${ROOT}/output/presentation/techflow-responsibility-boundary.pptx`;
const RENDER_DIR = `${TMP}/final-rendered`;
const LAYOUT_DIR = `${TMP}/final-layout`;
const INSPECT_OUTPUT = `${OUTPUT}.inspect.ndjson`;

const slideTexts = {
  1: [
    "ABLESTACK TECHFLOW · ISSUE #12",
    "TechFlow 책임 경계\nADR",
    "권한·상태·멱등성·실패를 세 계층으로 분리",
    "ADR-0001 · Accepted · 2026-07-30",
  ],
  2: [
    "결정: 제품 권한, 실행, 인프라 상태를 분리한다",
    "02",
    "Activepieces는 승인된 명령을 실행하지만 권한·정책·최종 상태를 결정하지 않는다.",
    "제품 제어면",
    "TechFlow Core\n요청 · 정책 · 승인 · 감사\n제품 요청 멱등성 · Reconcile",
    "인프라 권위면",
    "ABLESTACK/Mold API\n권한 재검증 · 작업 멱등성\nOperation · ResourceState",
    "실행 원칙",
    "Activepieces = Flow 실행  |  Callback = 힌트  |  ABLESTACK 상태 조회 후 결과 확정",
  ],
  3: [
    "세 계층의 책임을 원장 단위로 고정",
    "03",
    "각 계층은 자신의 상태만 권위 있게 소유하고 다른 계층의 결정을 대신하지 않는다.",
    "01",
    "TechFlow Core",
    "제품 요청 원장\n정책 · 승인 · 감사\nrequestId 중복 제거\n명령 수명주기 · Reconcile",
    "02",
    "Activepieces",
    "Flow 실행 원장\nTrigger · Queue · Worker\n제한 재시도 · Callback\n권한·최종 상태 판단 금지",
    "03",
    "ABLESTACK API",
    "인프라 상태 원장\n권한·전제조건 재검증\n작업 멱등성·비동기 상태\nResourceState 최종 권위",
    "결정 문서  |  ADR-0001 · Accepted · Issue #12",
  ],
  4: [
    "권위 데이터는 계층마다 하나만 둔다",
    "04",
    "같은 상태를 여러 저장소가 최종값으로 소유하지 않도록 계약을 분리한다.",
    "FlowRun 성공 ≠ 자원 성공",
  ],
  5: [
    "장애가 발생해도 권위 상태로 수렴한다",
    "05",
    "자동 재시도보다 상태 조회와 중복 방지가 우선이다.",
    "A",
    "중복 요청",
    "Core",
    "이벤트 지문으로 기존 요청 반환",
    "B",
    "Core·감사 장애",
    "Fail Closed",
    "변경 명령을 발행하지 않음",
    "C",
    "Worker·Queue 장애",
    "재개",
    "명령 만료 안에서 복구",
    "D",
    "API Timeout",
    "VERIFYING",
    "Blind Retry 없이 상태 조회",
    "E",
    "Callback 유실·역전",
    "Reconcile",
    "멱등 처리·권위 상태 재조회",
    "F",
    "부분 성공",
    "보상 필요",
    "새 명령·새 승인으로 처리",
  ],
  6: [
    "승인된 명령은 전달되고 결과는 다시 검증된다",
    "06",
    "권한과 상태는 실행 엔진을 통과해도 원래 소유자에게 남는다.",
    "요청",
    "Webhook\n사용자 · 이벤트\nrequestId",
    "TechFlow Core",
    "정책 · 승인 · 감사\nExecutionCommand\nVERIFYING · Reconcile",
    "Activepieces",
    "고정 FlowVersion\nQueue · Worker · Retry",
    "ABLESTACK API",
    "권한 · 전제조건\n멱등성 · 실제 작업",
    "ExecutionCommand",
    "서명 · 만료 · 멱등성 키",
    "제품 권한",
    "실행 계층",
  ],
  7: [
    "두 단계 멱등성과 세 상태 모델을 함께 적용",
    "07",
    "I1",
    "제품 요청 멱등성",
    "TechFlow Core\nWebhook · requestId\n요청 지문·승인 스냅샷\n새 명령 생성 방지",
    "I2",
    "인프라 작업 멱등성",
    "ABLESTACK API\ncommandId · idempotencyKey\n명령 지문 충돌 거부\n작업 한 번만 생성",
    "I3–I4",
    "상태 판정 규칙",
    "FlowRun = 실행 상태\nOperation = 작업 상태\nResourceState = 최종 상태\nTimeout은 VERIFYING",
    "중복 요청 차단",
    "중복 작업 차단",
    "권위 상태로 수렴",
  ],
  8: [
    "보안·테스트·운영 규칙도 ADR에 포함",
    "08",
    "경계는 문서 설명이 아니라 구현과 운영의 통과 기준이다.",
    "보안 통제",
    "단기·범위 제한 자격증명\n조회·변경 자격증명 분리\nWebhook·Callback 서명\n민감정보 로그 금지",
    "필수 테스트",
    "명령 계약·만료·변조\n멱등성 반복·승인 무효화\nTimeout·Callback 실패 주입\n테넌트 격리·감사 재구성",
    "운영 수렴",
    "DISPATCHED·UNKNOWN 조회\nReconciler·SLA 경보\nDLQ 민감값 제거\n수렴률·UNKNOWN 체류시간",
    "완료 기준  |  Blind Retry 0건 · 중복 작업 0건 · 요청부터 자원 상태까지 감사 추적 가능",
  ],
  9: [
    "ADR을 구현 계약으로 전환하는 순서",
    "09",
    "원장과 명령 계약을 먼저 만들고 Flow와 인프라 작업을 연결한다.",
    "1",
    "2",
    "3",
    "4",
    "요청 원장",
    "requestId · 감사\n정책 · 승인",
    "명령 계약",
    "서명 · 만료\n승인 스냅샷",
    "API 멱등성",
    "작업 조회\n권위 상태",
    "수렴 운영",
    "Reconciler · DLQ\n실패 주입",
    "후속 이슈는 ADR-0001을 참조하고 상태·멱등성·실패 주입 테스트를 완료 기준으로 사용",
  ],
  10: [
    "최종 결정",
    "Activepieces는 실행하고,\nTechFlow와 ABLESTACK이 권한과 상태를 소유한다.",
    "ADR-0001",
    "Accepted · 이 책임 경계를 모든 Core·Piece·ABLESTACK API 구현 규칙으로 적용",
    "ABLESTACK TechFlow · Issue #12",
    "ADR-0001 · 2026-07-30",
  ],
};

const tableRows = [
  ["구분", "TechFlow Core", "Activepieces", "ABLESTACK API"],
  ["권위", "제품 요청·정책", "Flow 실행", "자원 작업·상태"],
  ["Identity", "사용자·테넌트", "명령 자격증명", "권한 재검증"],
  ["State", "Request", "FlowRun", "Operation·Resource"],
  ["멱등성", "요청·이벤트", "동일 명령", "작업·지문"],
  ["승인", "판정·스냅샷", "판정 금지", "참조 검증"],
  ["재시도", "분류·정책", "제한 재시도", "중복 방지"],
  ["실패", "UNKNOWN·조정", "실행 상태", "권위 상태"],
  ["감사", "원장·상관관계", "실행 이력", "작업·자원 변경"],
];

const notesBySlide = {
  1: "ADR-0001은 TechFlow 실행 경계의 기준 문서다.",
  2: "제품 제어면, 실행면, 인프라 권위면을 분리한다.",
  3: "각 계층은 자신이 소유한 원장만 권위 있게 관리한다.",
  4: "FlowRun 성공은 실제 자원 성공과 동일하지 않다.",
  5: "장애 시 Blind Retry 대신 권위 상태 조회로 수렴한다.",
  6: "ExecutionCommand는 승인을 고정하고 Activepieces는 그대로 전달한다.",
  7: "제품 요청과 인프라 작업에 서로 다른 멱등성 경계를 적용한다.",
  8: "보안, 테스트와 운영 규칙을 구현 완료 기준으로 사용한다.",
  9: "원장, 명령, 멱등성, Reconcile 순서로 구현한다.",
  10: "ADR-0001을 모든 후속 Core, Piece, API 작업의 구현 규칙으로 적용한다.",
};

async function writeBlob(filePath, blob) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

async function main() {
  await fs.mkdir(path.dirname(OUTPUT), { recursive: true });
  await fs.mkdir(RENDER_DIR, { recursive: true });
  await fs.mkdir(LAYOUT_DIR, { recursive: true });

  const presentation = await PresentationFile.importPptx(
    await FileBlob.load(STARTER),
  );
  const snapshot = await presentation.inspect({
    kind: "slide,textbox,table,notes",
    maxChars: 200000,
  });
  const records = snapshot.ndjson
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => JSON.parse(line))
    .filter((record) => !["notice", "deck", "layout"].includes(record.kind));

  for (let slideNumber = 1; slideNumber <= 10; slideNumber += 1) {
    const textboxes = records.filter(
      (record) => record.kind === "textbox" && record.slide === slideNumber,
    );
    const replacements = slideTexts[slideNumber];
    if (textboxes.length !== replacements.length) {
      throw new Error(
        `Slide ${slideNumber}: expected ${replacements.length} textboxes, found ${textboxes.length}`,
      );
    }
    for (let index = 0; index < textboxes.length; index += 1) {
      presentation.resolve(textboxes[index].id).text = replacements[index];
    }

    const notes = records.find(
      (record) => record.kind === "notes" && record.slide === slideNumber,
    );
    if (!notes) {
      throw new Error(`Slide ${slideNumber}: speaker notes not found`);
    }
    presentation.resolve(notes.id).setText(
      [
        notesBySlide[slideNumber],
        "[Sources]",
        "- docs/adr/0001-techflow-activepieces-responsibility-boundary.md",
        "- docs/decisions/techflow-activepieces-responsibility-boundary.json",
        "- https://github.com/ablecloud-team/ablestack-techflow/issues/12",
        "[/Sources]",
      ].join("\n"),
    );
  }

  const tableRecord = records.find(
    (record) => record.kind === "table" && record.slide === 4,
  );
  if (!tableRecord) {
    throw new Error("Slide 4: authority table not found");
  }
  const authorityTable = presentation.resolve(tableRecord.id);
  for (let row = 0; row < tableRows.length; row += 1) {
    for (let column = 0; column < tableRows[row].length; column += 1) {
      authorityTable.cells.set(row, column, tableRows[row][column]);
    }
  }

  for (let index = 0; index < presentation.slides.items.length; index += 1) {
    const slide = presentation.slides.getItem(index);
    const stem = `slide-${String(index + 1).padStart(2, "0")}`;
    await writeBlob(
      `${RENDER_DIR}/${stem}.png`,
      await presentation.export({ slide, format: "png", scale: 1 }),
    );
    await fs.writeFile(
      `${LAYOUT_DIR}/${stem}.layout.json`,
      await (await slide.export({ format: "layout" })).text(),
      "utf8",
    );
  }

  const finalInspect = await presentation.inspect({
    kind: "deck,layout,slide,textbox,table,notes",
    maxChars: 200000,
  });
  await fs.writeFile(INSPECT_OUTPUT, `${finalInspect.ndjson}\n`, "utf8");

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(OUTPUT);
  console.log(OUTPUT);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
