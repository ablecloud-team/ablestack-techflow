import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const ROOT = process.argv[2]
  ? path.resolve(process.argv[2])
  : path.resolve(process.cwd(), "../../..");
const TMP = `${ROOT}/tmp/artifacts/issue-15`;
const STARTER = `${TMP}/template-starter.pptx`;
const OUTPUT = `${ROOT}/output/presentation/techflow-secret-management.pptx`;
const RENDER_DIR = `${TMP}/final-rendered`;
const LAYOUT_DIR = `${TMP}/final-layout`;
const INSPECT_OUTPUT = `${OUTPUT}.inspect.ndjson`;

const slideTexts = {
  1: [
    "ABLESTACK TECHFLOW · ISSUE #15",
    "Secret 수명주기\n검증",
    "비밀정보 저장·주입·교체·폐기와 사고 대응 운영 기준",
    "Ubuntu 24.04 · Activepieces 0.86.3 · 2026-07-31",
  ],
  2: [
    "결과: Secret 수명주기를 실서버에서 검증했습니다",
    "02",
    "보호 저장소, 현재·직전 Grace Period, 폐기, 감사와 재부팅 복구를 실제 외부 HTTPS 경로에서 확인했습니다.",
    "보호 저장소",
    "root:ablecloud 0640\n상위 0750\n배포 경로 Symlink",
    "Webhook 교체",
    "Grace 202 / 202\nRevoke 202 / 401\nGateway-only Restart",
    "최종 결과",
    "15 Controls PASS  |  Secret Leaks 0  |  6 Services Healthy  |  Reboot PASS",
  ],
  3: [
    "Secret의 권위와 실행 책임을 분리했습니다",
    "03",
    "운영자는 수명주기를 통제하고, 보호 저장소는 값을 보관하며, Activepieces는 주입된 값을 실행에만 사용합니다.",
    "01",
    "Protected Store",
    "/etc 전용 저장소\nroot 소유\n원자적 갱신\n일반 백업 제외",
    "02",
    "Secret Control",
    "Bootstrap\nRotate · Revoke\nRollback · Audit\nExposure Scan",
    "03",
    "AP Runtime",
    "Compose env_file\nConnection 암호화\nFlow 실행\nSecret 원장 아님",
    "운영 자산  |  ADR-0002 · secretctl · 원자적 갱신 · 노출 검사 · Runbook",
  ],
  4: [
    "Secret 유형마다 교체와 사고 대응 규칙을 고정",
    "04",
    "모든 값을 같은 방식으로 바꾸지 않습니다. 암호화 Root, 세션, 저장소, Webhook과 외부 Token의 영향에 맞춰 절차를 분리했습니다.",
    "실제 Secret 값은 Git·Issue·Flow·일반 백업·보고서·로그에 포함하지 않습니다.",
  ],
  5: [
    "생성부터 폐기까지 하나의 Runbook으로 반복",
    "05",
    "각 단계는 Secret 값을 출력하지 않으며 변경 범위, 검증 기준과 롤백 조건을 명시합니다.",
    "A",
    "분류·승인",
    "Owner",
    "유형 · 영향 · 작업 창",
    "B",
    "보호 저장",
    "bootstrap",
    "Store · Mode · Symlink",
    "C",
    "교체 준비",
    "Grace",
    "Current → Previous",
    "D",
    "발신 전환",
    "Verify",
    "Current 202 · Previous 202",
    "E",
    "직전 폐기",
    "Revoke",
    "Current 202 · Retired 401",
    "F",
    "복구·감사",
    "Reboot",
    "Health · Scan · Audit",
  ],
  6: [
    "Secret 값은 보호 경로에서 런타임으로만 이동합니다",
    "06",
    "운영 명령과 감사 로그에는 값이 남지 않으며, Webhook 교체는 Event Gateway만 재생성해 상태 저장소 영향을 제한합니다.",
    "승인 운영자",
    "분류 · 교체\n폐기 · 사고 대응\n값 출력 금지",
    "secretctl",
    "원자적 갱신\n값 없는 감사\nLifecycle Test",
    "Protected Store",
    "root:ablecloud\n0640 · Directory 0750",
    "Compose Runtime",
    "env_file 주입\nGateway-only Restart",
    "Decision Gate",
    "Grace 202/202 → Revoke 202/401",
    "통제 경로",
    "실행 경로",
  ],
  7: [
    "저장·교체·노출·복구 15개 검증을 통과",
    "07",
    "V1–5",
    "저장·기본 동작",
    "Store Migration PASS\n권한 PASS\n6 Secrets Present\nUnit 6/6\nCurrent 202",
    "V6-10",
    "교체·영향",
    "Previous 202\nCurrent 202\nRetired 401\nRedis Unchanged\nAsset Leaks 0",
    "V11–15",
    "회귀·복구",
    "Log Leaks 0\nHTTPS Regression PASS\nRestart PASS\nReboot PASS\nBackup Excludes .env",
    "저장·기본",
    "교체·영향",
    "회귀·복구",
  ],
  8: [
    "결정·구현·운영 증적을 일관된 자산으로 관리",
    "08",
    "다음 운영자가 동일한 저장·교체·폐기·검증을 수행할 수 있도록 실행 코드와 문서, 구조화 증적을 함께 제공합니다.",
    "실행 자산",
    "secretctl · secret_env\nsecret_scan · verify-secrets\nGateway Dual Secret\nUnit Tests 6/6",
    "운영 문서",
    "ADR-0002\nSecret Lifecycle Runbook\n환경 기준선 갱신\n사고 대응 · 백업 경계",
    "검증 증적",
    "구조화 JSON\nPDF 보고서 · PPTX\nSHA-256 Manifest\n시각·Overflow 검사",
    "보안 기준  |  Secret 미커밋 · 명령행 미전달 · 값 없는 감사 · 일반 백업 제외 · 노출 0건",
  ],
  9: [
    "다음 단계는 백업 복구 훈련과 첫 업무 Flow",
    "09",
    "Issue #15로 Secret 운영 통제를 확보했습니다. 다음은 데이터·Secret 복구 가능성을 증명한 뒤 GitHub PR Merge Flow를 실증하는 것입니다.",
    "1",
    "2",
    "3",
    "4",
    "Backup",
    "#16 DB·Redis\n격리 복구 훈련",
    "Observe",
    "#17 로그·메트릭\n#18 버전 정책",
    "First Flow",
    "#19 GitHub PR\nMerge Webhook",
    "Productize",
    "Secret Provider\nVault · KMS 연계",
    "Issue #15 완료 기준 = 보호 저장소 + Grace/폐기 + 감사 + 노출 0 + 재시작·재부팅 복구",
  ],
  10: [
    "최종 결과",
    "비밀정보 수명주기를\n운영 가능한 기준으로 확정했습니다.",
    "ISSUE #15",
    "VALIDATED · 15 CONTROLS PASS · SECRET LEAKS 0 · REBOOT PASS",
    "ABLESTACK TechFlow · Secret Lifecycle",
    "Issue #15 · 2026-07-31",
  ],
};

const tableRows = [
  ["분류", "대표 값", "교체 방식", "유출 시"],
  ["S1 Root", "Encryption Key", "복구 계획 선행", "즉시 격리"],
  ["S2 Session", "JWT · API Key", "작업 창 + 재시작", "세션 무효화"],
  ["S3 State", "DB · Redis", "양쪽 자격증명 조정", "연결 폐기"],
  ["S4 Webhook", "HMAC Secret", "Current + Previous", "Grace 없이 폐기"],
  ["S5 External", "GitHub · AI Token", "발급 → 전환 → 폐기", "제공자 폐기"],
  ["S6 Connection", "Activepieces", "재인가", "Connection 무효화"],
  ["감사", "변경 Event", "값 없는 JSONL", "사고 기록"],
  ["백업", "Secret Recovery", "일반 백업과 분리", "격리·복원 훈련"],
];

const notesBySlide = {
  1: "Issue #15는 Secret 저장·주입·교체·폐기와 사고 대응을 실서버에 구현하고 검증한 작업입니다.",
  2: "완료 판정은 보호 저장소, Grace Period, 폐기, 노출 0건과 재부팅 복구를 포함합니다.",
  3: "Secret 수명주기 권위는 TechFlow에 두고 Activepieces는 실행 시 주입된 값을 사용합니다.",
  4: "Secret 유형별 영향에 따라 교체 방식과 사고 대응을 분리했습니다.",
  5: "운영자는 동일 Runbook으로 저장, 교체, 폐기, 복구와 감사를 반복할 수 있습니다.",
  6: "Secret은 보호 저장소에서 런타임으로만 이동하고 감사에는 값이 남지 않습니다.",
  7: "저장, 교체, 영향 제한, 노출 검사와 재부팅 복구까지 15개 검증을 통과했습니다.",
  8: "ADR, 코드, Runbook, JSON, PDF, PPTX와 Manifest를 일관된 검증 자산으로 관리합니다.",
  9: "다음 단계는 Issue #16 백업·복구 훈련 후 첫 GitHub PR Merge Flow를 실증하는 것입니다.",
  10: "Issue #15는 Secret 수명주기를 운영 가능한 기준으로 확정한 상태로 종료합니다.",
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
        "- docs/adr/0002-techflow-secret-lifecycle.md",
        "- docs/decisions/techflow-secret-management.json",
        "- docs/reports/issue-15-secret-management-validation.md",
        "- docs/runbooks/secret-lifecycle.md",
        "- https://github.com/ablecloud-team/ablestack-techflow/issues/15",
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
