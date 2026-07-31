import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const ROOT = path.resolve(process.argv[2]);
const TMP = `${ROOT}/tmp/artifacts/issue-18`;
const STARTER = `${TMP}/template-starter.pptx`;
const OUTPUT = `${ROOT}/output/presentation/techflow-image-version-lock.pptx`;
const RENDER_DIR = `${TMP}/final-rendered`;
const LAYOUT_DIR = `${TMP}/final-layout`;
const INSPECT_OUTPUT = `${OUTPUT}.inspect.ndjson`;

const slideTexts = {
  1: [
    "ABLESTACK TECHFLOW · ISSUE #18",
    "버전·이미지 Digest\n고정과 롤백",
    "같은 승인 이미지를 반복 배포하고 직전 상태로 복귀",
    "Ubuntu 24.04 · Activepieces 0.86.3 · 2026-07-31",
  ],
  2: [
    "결과: 여섯 서비스를 불변 이미지 조합으로 고정했습니다",
    "Tag만 사용하던 배포를 검토된 잠금 파일과 무빌드 배포·롤백 절차로 전환했습니다.",
    "고정 상태",
    "6 Services Locked\n6/6 Healthy\nHTTPS 200",
    "실제 드릴",
    "Repeat IDs Equal\nRollback PASS\nVolumes Unchanged",
    "최종 결과",
    "13 Controls PASS  |  Observer Alerts 0  |  Secret Leaks 0",
  ],
  3: [
    "선택·배포·검증을 분리해 변경을 통제합니다",
    "버전 선택과 승인, 실제 실행, 상태 검증을 분리하고 Activepieces에는 Flow 실행 책임만 둡니다.",
    "01",
    "Select & Lock",
    "Release Review\nTag + Registry Digest\nGateway Image ID",
    "02",
    "Deploy",
    "State Backup\nPull External Images\nCompose --no-build",
    "03",
    "Verify & Recover",
    "Health · Image IDs\nRuntime Locks\nLocal-only Rollback",
    "운영 경계  |  잠금 승인과 데이터 호환성 판단은 TechFlow가 소유",
  ],
  4: [
    "사람이 읽는 버전과 기계가 검증하는 식별자를 함께 둡니다",
    "외부 이미지는 Tag+Registry Digest, 자체 Gateway는 M0 승인 Image ID로 고정했습니다.",
    "Gateway는 고객 배포 전에 승인 Registry Digest로 전환합니다.",
  ],
  5: [
    "업그레이드와 롤백은 하나의 검증된 순서로 반복합니다",
    "배포 전 백업부터 최종 복귀까지 같은 잠금·Health·Volume 기준으로 판정합니다.",
    "A",
    "Review",
    "Release",
    "Notes · Security · Schema",
    "B",
    "Lock",
    "Images",
    "Tag+Digest · Image ID",
    "C",
    "Backup",
    "State",
    "Runtime Lock · DB · Redis",
    "D",
    "Deploy",
    "No Build",
    "Pull · Up · Health",
    "E",
    "Verify",
    "Runtime",
    "6 IDs · HTTPS · Observer",
    "F",
    "Rollback",
    "Local Only",
    "Previous Lock · Recheck",
  ],
  6: [
    "릴리스 증적은 이미지와 판정만 남기도록 최소화했습니다",
    "잠금과 드릴 기록에는 이미지 식별자·Health·시각만 저장하고 Secret, Payload와 원문 로그는 제외합니다.",
    "Release Inputs",
    "Version · Digest\nGateway Image ID",
    "Reviewed Lock",
    "Source Consistency\nPlatform · Policy",
    "Runtime Evidence",
    "Previous · Current\nHistory · Drill",
    "Operator",
    "Deploy · Verify\nRollback · Recover",
    "No Secrets",
    "No Raw Logs",
    "승인 경계",
    "운영 경계",
  ],
  7: [
    "재현성·복구·보안 13개 검증을 모두 통과했습니다",
    "V1–4",
    "잠금 기반",
    "Schema · Source PASS\nUnit Tests 7\nRegistry Digests\n6 Runtime Images",
    "V5–8",
    "배포·복구",
    "6 Health PASS\nRepeat IDs Equal\nRollback PASS\nFinal Release PASS",
    "V9–13",
    "상태·보안",
    "3 Volumes Preserved\nBackup Manifest\nHTTPS 200 · Alerts 0\nSecret Scan PASS",
    "잠금·소스",
    "반복·롤백",
    "상태·보안",
  ],
  8: [
    "코드·운영 절차·완료 증적을 하나의 릴리스 자산으로 관리합니다",
    "다음 운영자가 같은 이미지 조합을 배포하고 장애 시 같은 기준으로 복귀할 수 있습니다.",
    "실행 자산",
    "image-lock.json\nrelease_lock.py\ndeploy · rollback · drill",
    "운영 문서",
    "ADR-0005\nUpgrade·Rollback Runbook\n호환성·승인 정책",
    "검증 증적",
    "구조화 JSON\nPDF 보고서 · PPTX\nSHA-256 Manifest",
    "보안 기준  |  0640 · Secret/Payload/원문 로그 제외 · Fail Closed",
  ],
  9: [
    "이제 고정된 실행 기반에서 첫 사내 업무 Flow로 이동합니다",
    "Issue #18로 실행 환경의 버전과 복구 경로가 확정됐습니다. 다음은 GitHub PR Merge Webhook을 실제 업무와 연결합니다.",
    "1",
    "2",
    "3",
    "4",
    "Observe",
    "#17 상태·경보\n장애·복구 추적",
    "Pin",
    "#18 Digest Lock\nNo-build Rollback",
    "First Flow",
    "#19 GitHub PR\nMerge Webhook",
    "Productize",
    "Gateway Registry\nSBOM · Sign · Scan",
    "Issue #18 완료 기준 = 반복 이미지 동일 + 롤백 PASS + Volume 보존 + 누출 0",
  ],
  10: [
    "최종 결과",
    "같은 승인 이미지를 재현하고\n직전 상태로 복귀하는 기반을 확정했습니다.",
    "ISSUE #18",
    "VALIDATED · 6/6 HEALTHY · 13 CONTROLS PASS · HTTPS 200",
    "ABLESTACK TechFlow · Immutable Release Foundation",
    "Issue #18 · 2026-07-31",
  ],
};

const tableRows = [
  ["대상", "버전", "불변 기준", "배포 방식"],
  ["PostgreSQL", "0.8.0-pg14", "Registry Digest", "Pull"],
  ["Redis", "7.0.7", "Registry Digest", "Pull"],
  ["AP App", "0.86.3", "Registry Digest", "Pull"],
  ["AP Worker", "0.86.3", "Registry Digest", "Pull"],
  ["Gateway", "0.1.0", "Local Image ID", "No build"],
  ["Gateway Base", "Python 3.12.11", "Registry Digest", "Build input"],
  ["Caddy", "2.8.4", "Registry Digest", "Pull"],
  ["Platform", "linux/amd64", "Release Lock", "Validated"],
];

const notesBySlide = {
  1: "Issue #18은 Tag만으로 배포하던 여섯 서비스를 불변 이미지 식별자로 고정하고 검증된 롤백 경로를 만든 작업입니다.",
  2: "동일 잠금 반복 배포, 직전 Runtime Lock 롤백, 목표 릴리스 복귀와 세 Volume 보존을 실제 서버에서 검증했습니다.",
  3: "개발자는 버전을 선택하고 운영자는 승인 잠금만 배포하며 스크립트가 이미지와 Health를 검증합니다.",
  4: "외부 이미지는 Tag와 Registry Digest를 함께 사용하고 현재 Gateway는 승인된 로컬 Image ID를 사용합니다.",
  5: "업그레이드는 검토, 잠금, 백업, 무빌드 배포, 검증, 로컬 전용 롤백 순서로 수행합니다.",
  6: "릴리스 증적에는 Secret과 업무 Payload를 넣지 않고 이미지 식별자와 안전한 판정만 보관합니다.",
  7: "잠금, 반복 배포, 롤백, 상태 보존, HTTPS, 관측성과 Secret Scan을 포함한 13개 검증을 통과했습니다.",
  8: "실행 코드, ADR, Runbook, 구조화 JSON, PDF, PPTX와 Manifest를 일관된 자산으로 관리합니다.",
  9: "다음은 Issue #19 GitHub PR Merge Webhook이며 제품화 Track에서는 Gateway Registry와 공급망 Gate를 준비합니다.",
  10: "Issue #18은 같은 승인 이미지를 반복 배포하고 직전 상태로 복귀할 수 있는 기반이 검증된 상태로 종료됩니다.",
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
  const snapshot = await presentation.inspect({ kind: "slide,textbox,table,notes", maxChars: 500000 });
  const records = snapshot.ndjson.split(/\r?\n/).filter(Boolean).map(JSON.parse)
    .filter((record) => !["notice", "deck", "layout"].includes(record.kind));

  for (let slideNumber = 1; slideNumber <= 10; slideNumber += 1) {
    const textboxes = records.filter((record) => record.kind === "textbox" && record.slide === slideNumber)
      .filter((record) => !(record.text.trim() === String(slideNumber).padStart(2, "0") && record.bbox?.[0] > 1100 && record.bbox?.[1] > 600));
    const replacements = slideTexts[slideNumber];
    if (textboxes.length !== replacements.length) {
      throw new Error(`Slide ${slideNumber}: expected ${replacements.length} textboxes, found ${textboxes.length}`);
    }
    textboxes.forEach((record, index) => { presentation.resolve(record.id).text = replacements[index]; });
    const notes = records.find((record) => record.kind === "notes" && record.slide === slideNumber);
    if (!notes) throw new Error(`Slide ${slideNumber}: speaker notes not found`);
    presentation.resolve(notes.id).setText([
      notesBySlide[slideNumber], "[Sources]",
      "- docs/adr/0005-techflow-image-version-lock.md",
      "- docs/decisions/techflow-image-version-lock.json",
      "- docs/reports/issue-18-image-digest-validation.md",
      "- docs/runbooks/image-version-upgrade-rollback.md",
      "- https://github.com/ablecloud-team/ablestack-techflow/issues/18",
      "[/Sources]",
    ].join("\n"));
  }

  const tableRecord = records.find((record) => record.kind === "table" && record.slide === 4);
  if (!tableRecord) throw new Error("Slide 4: image lock table not found");
  const table = presentation.resolve(tableRecord.id);
  for (let row = 0; row < tableRows.length; row += 1) {
    for (let column = 0; column < tableRows[row].length; column += 1) table.cells.set(row, column, tableRows[row][column]);
  }

  for (let index = 0; index < presentation.slides.items.length; index += 1) {
    const slide = presentation.slides.getItem(index);
    const stem = `slide-${String(index + 1).padStart(2, "0")}`;
    await writeBlob(`${RENDER_DIR}/${stem}.png`, await presentation.export({ slide, format: "png", scale: 1 }));
    await fs.writeFile(`${LAYOUT_DIR}/${stem}.layout.json`, await (await slide.export({ format: "layout" })).text(), "utf8");
  }
  const finalInspect = await presentation.inspect({ kind: "deck,layout,slide,textbox,table,notes", maxChars: 500000 });
  await fs.writeFile(INSPECT_OUTPUT, `${finalInspect.ndjson}\n`, "utf8");
  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(OUTPUT);
  console.log(OUTPUT);
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
