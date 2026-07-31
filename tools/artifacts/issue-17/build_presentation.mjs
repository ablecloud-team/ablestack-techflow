import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const ROOT = process.argv[2]
  ? path.resolve(process.argv[2])
  : path.resolve(process.cwd(), "../../..");
const TMP = `${ROOT}/tmp/artifacts/issue-17`;
const STARTER = `${TMP}/template-starter.pptx`;
const OUTPUT = `${ROOT}/output/presentation/techflow-observability.pptx`;
const RENDER_DIR = `${TMP}/final-rendered`;
const LAYOUT_DIR = `${TMP}/final-layout`;
const INSPECT_OUTPUT = `${OUTPUT}.inspect.ndjson`;

const slideTexts = {
  1: [
    "ABLESTACK TECHFLOW · ISSUE #17",
    "로그·메트릭·상태\n점검 구성",
    "장애의 발생·원인·복구를 1분 주기로 추적",
    "Ubuntu 24.04 · Activepieces 0.86.3 · 2026-07-31",
  ],
  2: [
    "결과: Gateway 장애를 감지하고 복구까지 추적했습니다",
    "02",
    "서비스·엔드포인트·데이터 계층·백업을 한 번에 수집하고 경보 발생과 해제를 같은 키로 연결했습니다.",
    "정상 상태",
    "6/6 Services Healthy\n3 Endpoints HTTP 200\nCritical 0 · Warning 0",
    "장애 실증",
    "Gateway Stop\nCritical Exit 2\n원인 2건 식별",
    "최종 결과",
    "43 Metric Series  |  12 Controls PASS  |  Secret Leaks 0  |  HTTPS 200",
  ],
  3: [
    "수집·판정·통지를 서로 다른 책임으로 분리했습니다",
    "03",
    "Observer는 허용된 상태와 집계값만 만들고 systemd는 주기 실행과 로컬 실패 통지를 담당합니다.",
    "01",
    "Collect",
    "Docker · HTTP\nPostgreSQL · Redis\nBackup · Safe Log Counts",
    "02",
    "Evaluate",
    "Warning · Critical\nStable Alert Keys\nStrict Exit Code",
    "03",
    "Record",
    "status · metrics\nCurrent Alerts\nTransitions · Journal",
    "운영 경계  |  Observer는 Flow·가상자원 상태를 변경하지 않음",
  ],
  4: [
    "장애 판정은 고정 임계값과 안전한 집계로 재현됩니다",
    "04",
    "서비스·Endpoint·DB·Redis·Backup·Flow·Webhook을 공통 정책으로 판정하고 원문 로그와 Payload는 저장하지 않습니다.",
    "현재 Flow 실행 이력이 없어 상태별 실행 수와 p95 지연은 빈 시계열입니다.",
  ],
  5: [
    "감지부터 해제까지 하나의 Runbook으로 반복합니다",
    "05",
    "운영자는 고정 경보 키를 따라 컴포넌트를 확인하고 복구 후 같은 키의 Resolved 전이를 확인합니다.",
    "A",
    "Collect",
    "Baseline",
    "1분 Timer · Strict",
    "B",
    "Detect",
    "Alert",
    "Critical Exit 2",
    "C",
    "Identify",
    "Cause",
    "Service · Endpoint",
    "D",
    "Notify",
    "Journal",
    "systemd OnFailure",
    "E",
    "Recover",
    "Health",
    "Gateway Start · 6/6",
    "F",
    "Resolve",
    "Transition",
    "Opened → Resolved",
  ],
  6: [
    "관측 데이터는 운영 원문과 만나지 않도록 최소화했습니다",
    "06",
    "정해진 상태·집계만 0640 파일에 원자적으로 저장하고 Flow ID, Payload, 사용자 정보와 원문 로그는 복제하지 않습니다.",
    "Runtime Sources",
    "Docker · HTTP\nDB · Redis · Backup",
    "Safe Aggregation",
    "Health · Counts\nDuration · Capacity",
    "Observer State",
    "JSON · Prometheus\nStable Alert Keys",
    "Operator",
    "Status · Journal\nRunbook Response",
    "Allowlist",
    "No Raw Payload",
    "수집 경계",
    "운영 경계",
  ],
  7: [
    "관측성과 보안 12개 검증을 모두 통과했습니다",
    "07",
    "V1–4",
    "수집 기반",
    "Unit Tests 7\nTimer Active\n6 Health PASS\nEndpoints 200",
    "V5–8",
    "메트릭·장애",
    "DB · Redis · Backup\nPrometheus PASS\nFailure Detected\nTransitions PASS",
    "V9–12",
    "알림·보안",
    "OnFailure PASS\nRecovery PASS\nLogs Bounded\nSecret Scan PASS",
    "수집·Timer",
    "장애·복구",
    "보안·로그",
  ],
  8: [
    "코드·운영 절차·완료 증적을 하나의 자산 체계로 관리합니다",
    "08",
    "다음 운영자가 동일한 설치·점검·훈련·복구를 재현하도록 실행 코드와 판단 기준을 함께 제공합니다.",
    "실행 자산",
    "observer.py\ninstall · verify · drill\nSystemd Service · Timer",
    "운영 문서",
    "ADR-0004\nObservability Runbook\n장애·경보 정책\n롤백 절차",
    "검증 증적",
    "구조화 JSON\nPDF 보고서 · PPTX\nSHA-256 Manifest\n시각·Overflow 검사",
    "보안 기준  |  Secret·Payload·원문 로그 제외 · 0640 · 허용된 Label만 사용",
  ],
  9: [
    "이제 관측 기반 위에서 첫 사내 업무 Flow로 이동합니다",
    "09",
    "Issue #17로 실행 기반의 상태를 볼 수 있게 됐습니다. 다음은 버전을 고정하고 GitHub PR Merge Flow에서 실제 실행 데이터를 만듭니다.",
    "1",
    "2",
    "3",
    "4",
    "Observe",
    "#17 로그·메트릭\n경보·복구",
    "Pin",
    "#18 이미지 Digest\n업그레이드 정책",
    "First Flow",
    "#19 GitHub PR\nMerge Webhook",
    "Extend",
    "Flow p95 검증\n중앙 수집·알림",
    "Issue #17 완료 기준 = 1분 수집 + 원인 식별 + OnFailure + Resolved + Secret 누출 0",
  ],
  10: [
    "최종 결과",
    "장애를 발견하는 수준을 넘어\n원인과 복구를 추적하는 기반을 확정했습니다.",
    "ISSUE #17",
    "VALIDATED · 6/6 HEALTHY · 43 METRIC SERIES · 12 CONTROLS PASS",
    "ABLESTACK TechFlow · Observability Foundation",
    "Issue #17 · 2026-07-31",
  ],
};

const tableRows = [
  ["ID", "대상", "경보 기준", "심각도"],
  ["H1", "Service", "Missing · Unhealthy", "Critical"],
  ["H2", "Internal", "HTTP != 200", "Critical"],
  ["H3", "Public", "HTTP != 200", "Warning"],
  ["R1", "Host", "Disk 85% / 95%", "W / C"],
  ["R2", "Memory", "Available 15% / 5%", "W / C"],
  ["D1", "DB · Redis", "Unreachable", "Critical"],
  ["B1", "Backup", "Failed · > 26h", "Critical"],
  ["F1", "Flow", "Failures 1 / 5", "W / C"],
];

const notesBySlide = {
  1: "Issue #17은 Activepieces 기반 TechFlow의 실행 상태를 1분마다 수집하고 장애의 발생, 원인, 복구를 추적하는 기반을 만든 작업입니다.",
  2: "정상 상태에서 6개 서비스와 3개 Endpoint가 정상이며 Gateway 중단 시 Critical 2건을 감지하고 복구 후 해제했습니다.",
  3: "Observer는 읽기 전용 수집과 판정만 수행하며 systemd가 주기 실행과 로컬 실패 통지를 담당합니다.",
  4: "경보 임계값은 고정 정책으로 관리하고 Flow Payload와 원문 로그를 저장하지 않습니다.",
  5: "수집, 감지, 원인 식별, 통지, 복구, 해제를 하나의 반복 가능한 Runbook으로 구성했습니다.",
  6: "관측 파일은 허용된 집계만 포함하며 0640 권한과 원자적 교체를 적용합니다.",
  7: "단위 테스트, Timer, Health, 메트릭, 장애 훈련, 복구, 로그 한도와 Secret Scan을 포함한 12개 검증을 통과했습니다.",
  8: "코드, systemd, ADR, Runbook, 구조화 JSON, PDF, PPTX와 Manifest를 일관된 자산으로 관리합니다.",
  9: "다음은 Issue #18 버전 고정과 Issue #19 GitHub PR Merge Flow이며 실제 Flow 실행 데이터로 p95를 검증합니다.",
  10: "Issue #17은 장애를 감지하고 원인과 복구를 추적하는 운영 기반이 검증된 상태로 종료됩니다.",
};

async function writeBlob(filePath, blob) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

async function main() {
  await fs.mkdir(path.dirname(OUTPUT), { recursive: true });
  await fs.mkdir(RENDER_DIR, { recursive: true });
  await fs.mkdir(LAYOUT_DIR, { recursive: true });

  const presentation = await PresentationFile.importPptx(await FileBlob.load(STARTER));
  const snapshot = await presentation.inspect({
    kind: "slide,textbox,table,notes",
    maxChars: 500000,
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
    presentation.resolve(notes.id).setText([
      notesBySlide[slideNumber],
      "[Sources]",
      "- docs/adr/0004-techflow-observability.md",
      "- docs/decisions/techflow-observability.json",
      "- docs/reports/issue-17-observability-validation.md",
      "- docs/runbooks/observability.md",
      "- https://github.com/ablecloud-team/ablestack-techflow/issues/17",
      "[/Sources]",
    ].join("\n"));
  }

  const tableRecord = records.find(
    (record) => record.kind === "table" && record.slide === 4,
  );
  if (!tableRecord) {
    throw new Error("Slide 4: policy table not found");
  }
  const policyTable = presentation.resolve(tableRecord.id);
  for (let row = 0; row < tableRows.length; row += 1) {
    for (let column = 0; column < tableRows[row].length; column += 1) {
      policyTable.cells.set(row, column, tableRows[row][column]);
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
    maxChars: 500000,
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
