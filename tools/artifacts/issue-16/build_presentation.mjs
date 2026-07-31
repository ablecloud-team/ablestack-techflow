import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const ROOT = process.argv[2]
  ? path.resolve(process.argv[2])
  : path.resolve(process.cwd(), "../../..");
const TMP = `${ROOT}/tmp/artifacts/issue-16`;
const STARTER = `${TMP}/template-starter.pptx`;
const OUTPUT = `${ROOT}/output/presentation/techflow-backup-recovery.pptx`;
const RENDER_DIR = `${TMP}/final-rendered`;
const LAYOUT_DIR = `${TMP}/final-layout`;
const INSPECT_OUTPUT = `${OUTPUT}.inspect.ndjson`;

const slideTexts = {
  1: [
    "ABLESTACK TECHFLOW · ISSUE #16",
    "상태 백업·복구\n검증",
    "PostgreSQL·Redis 무중단 백업과 운영 비영향 격리 복구",
    "Ubuntu 24.04 · Activepieces 0.86.3 · 2026-07-31",
  ],
  2: [
    "결과: 운영을 멈추지 않고 40초 안에 복구했습니다",
    "02",
    "실제 PostgreSQL·Redis Snapshot을 별도 Network·Volume·Container에 복원하고 운영 상태가 유지되는지 확인했습니다.",
    "정기 백업",
    "매일 02:30 UTC\n정기 7일 보존\nSHA-256 검증",
    "격리 복구",
    "공개 Port 0\n운영 Container 유지\n임시 자원 자동 정리",
    "최종 결과",
    "RTO 40초  |  15 Controls PASS  |  6 Services Healthy  |  HTTPS 200",
  ],
  3: [
    "백업·복구·Secret을 서로 다른 경계로 분리",
    "03",
    "상태 Archive는 데이터만 담고, 복구 환경은 운영과 분리하며, 암호화 Root는 별도 Escrow로 보호합니다.",
    "01",
    "State Backup",
    "PostgreSQL Dump\nRedis RDB\nManifest · SHA-256\nSecret 원문 제외",
    "02",
    "Recovery Drill",
    "Internal Network\nTemporary Volumes\nProbe Verification\nAutomatic Cleanup",
    "03",
    "Secret Escrow",
    "OpenPGP AES-256\nPassphrase 분리\n격리 복호화\n운영 원본 미변경",
    "운영 자산  |  ADR-0003 · Backup Timer · Recovery Drill · Secret Escrow · Runbook",
  ],
  4: [
    "복구 성공은 파일 생성이 아니라 재사용 가능성으로 판정",
    "04",
    "Snapshot 무결성, 격리 복원, Probe 일치, 운영 Health와 임시 자원 정리까지 모두 통과해야 합니다.",
    "PostgreSQL과 Redis는 각각 일관된 Snapshot이며 두 저장소의 분산 트랜잭션 시점은 보장하지 않습니다.",
  ],
  5: [
    "Backup부터 운영 재확인까지 하나의 Runbook으로 반복",
    "05",
    "자동화는 운영 Volume을 덮어쓰지 않고 단계별 실패 조건과 정리 정책을 명시합니다.",
    "A",
    "Probe 기록",
    "Source",
    "DB · Redis 동일 ID",
    "B",
    "Snapshot",
    "Backup",
    "pg_dump · Redis RDB",
    "C",
    "무결성",
    "Verify",
    "Manifest · SHA-256",
    "D",
    "격리 복원",
    "Restore",
    "Internal Network · Volumes",
    "E",
    "성공 판정",
    "Probe",
    "Table · RDB · Same ID",
    "F",
    "정리·운영",
    "Cleanup",
    "0 Resources · Health",
  ],
  6: [
    "복구 데이터는 운영과 만나는 지점이 없습니다",
    "06",
    "Archive 검증 후 내부 전용 Docker 환경에만 복원하고 공개 Port 없이 Probe·Health를 확인한 뒤 모두 제거합니다.",
    "운영 State",
    "PostgreSQL · Redis\nContainer ID 유지\n서비스 중단 없음",
    "Backup Archive",
    "Custom Dump · RDB\nChecksum · Secret 제외",
    "Isolated Restore",
    "Internal Network\nTemporary Volumes",
    "Verification",
    "Table · RDB\nCross-store Probe",
    "Decision Gate",
    "RTO ≤ 15분 → Health PASS",
    "운영 경계",
    "복구 경계",
  ],
  7: [
    "백업·복원·보안 15개 검증을 통과",
    "07",
    "V1–5",
    "백업·정기 실행",
    "PostgreSQL PASS\nRedis RDB PASS\nChecksums PASS\nSecrets Excluded\nTimer Success",
    "V6-10",
    "격리 복구",
    "DB Restore PASS\nRDB Restore PASS\nProbe PASS\nPublished Ports 0\nContainers Unchanged",
    "V11–15",
    "회귀·보안",
    "Health PASS\nCleanup 0\nEscrow PASS\nHTTPS 200\nLegacy Archive Removed",
    "백업·정기",
    "격리·검증",
    "회귀·보안",
  ],
  8: [
    "정책·실행·복구 증적을 하나의 자산 체계로 관리",
    "08",
    "다음 운영자가 동일한 백업과 격리 복구를 재현하도록 코드, Systemd, Runbook과 구조화 증적을 함께 제공합니다.",
    "실행 자산",
    "backup-state\nrestore-state-drill\ntest-backup-recovery\nSystemd Timer",
    "운영 문서",
    "ADR-0003\nBackup·Recovery Runbook\n환경 기준선 갱신\n장애 처리 · RPO·RTO",
    "검증 증적",
    "구조화 JSON\nPDF 보고서 · PPTX\nSHA-256 Manifest\n시각·Overflow 검사",
    "보안 기준  |  Secret 원문 제외 · 공개 Port 0 · 운영 Volume 미사용 · 평문 임시 파일 제거",
  ],
  9: [
    "다음 단계는 관측 가능성을 완성하고 첫 업무 Flow로 이동",
    "09",
    "Issue #16으로 복구 가능성을 증명했습니다. 다음은 백업 실패와 상태를 관측 체계에 연결한 뒤 GitHub PR Merge Flow를 실증합니다.",
    "1",
    "2",
    "3",
    "4",
    "Observe",
    "#17 로그·메트릭\nBackup 상태·알림",
    "Pin",
    "#18 이미지 Digest\n회귀 정책",
    "First Flow",
    "#19 GitHub PR\nMerge Webhook",
    "Productize",
    "Off-host Backup\nVault · DR 정책",
    "Issue #16 완료 기준 = 정기 Backup + 격리 Restore + RTO 40초 + 운영 비영향 + Secret 분리",
  ],
  10: [
    "최종 결과",
    "상태 백업과 격리 복구를\n운영 가능한 기준으로 확정했습니다.",
    "ISSUE #16",
    "VALIDATED · RTO 40 SEC · 15 CONTROLS PASS · ZERO RECOVERY RESOURCES",
    "ABLESTACK TechFlow · State Backup & Recovery",
    "Issue #16 · 2026-07-31",
  ],
};

const tableRows = [
  ["ID", "대상", "성공 기준", "결과"],
  ["B1", "PostgreSQL", "Dump · SHA-256", "PASS"],
  ["B2", "Redis", "RDB Load", "PASS"],
  ["B3", "Archive", "Secret 없음", "PASS"],
  ["R1", "PG Restore", "80 · Probe", "PASS"],
  ["R2", "Redis Restore", "RDB · Probe", "PASS"],
  ["R3", "Isolation", "Port 0 · ID 유지", "PASS"],
  ["S1", "Escrow", "AES256 · Hash", "PASS"],
  ["O1", "Runtime", "6 Health · 200", "PASS"],
];

const notesBySlide = {
  1: "Issue #16은 PostgreSQL·Redis 상태를 무중단 백업하고 운영과 분리된 환경에 복원해 실제 복구 가능성을 검증한 작업입니다.",
  2: "복구는 40초에 완료됐고 운영 컨테이너와 6개 서비스 Health가 유지됐습니다.",
  3: "상태 Archive, 격리 복구 환경과 Secret Escrow를 서로 다른 보안 경계로 분리했습니다.",
  4: "파일 생성만으로 성공을 인정하지 않고 Snapshot 무결성, Probe, 운영 Health와 정리까지 판정합니다.",
  5: "Probe 기록부터 Backup, Restore, 성공 판정과 정리를 하나의 Runbook으로 반복합니다.",
  6: "격리 복구는 내부 Network와 임시 Volume만 사용하며 운영 Volume이나 공개 Port를 사용하지 않습니다.",
  7: "정기 실행, 양쪽 저장소 복원, 보안과 회귀를 포함한 15개 검증을 통과했습니다.",
  8: "ADR, 코드, Systemd, Runbook, JSON, PDF, PPTX와 Manifest를 일관된 자산으로 관리합니다.",
  9: "다음 단계는 Issue #17 관측 체계, Issue #18 버전 정책과 Issue #19 첫 업무 Flow입니다.",
  10: "Issue #16은 상태 백업과 격리 복구를 운영 가능한 기준으로 확정한 상태로 종료합니다.",
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
    presentation.resolve(notes.id).setText(
      [
        notesBySlide[slideNumber],
        "[Sources]",
        "- docs/adr/0003-techflow-state-backup-recovery.md",
        "- docs/decisions/techflow-backup-recovery.json",
        "- docs/reports/issue-16-backup-recovery-validation.md",
        "- docs/runbooks/state-backup-recovery.md",
        "- https://github.com/ablecloud-team/ablestack-techflow/issues/16",
        "[/Sources]",
      ].join("\n"),
    );
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
