import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const ROOT = process.argv[2]
  ? path.resolve(process.argv[2])
  : path.resolve(process.cwd(), "../../..");
const TMP = `${ROOT}/tmp/artifacts/issue-14`;
const STARTER = `${TMP}/template-starter.pptx`;
const OUTPUT = `${ROOT}/output/presentation/https-webhook-ingress.pptx`;
const RENDER_DIR = `${TMP}/final-rendered`;
const LAYOUT_DIR = `${TMP}/final-layout`;
const INSPECT_OUTPUT = `${OUTPUT}.inspect.ndjson`;

const slideTexts = {
  1: [
    "ABLESTACK TECHFLOW · ISSUE #14",
    "HTTPS·Webhook\nIngress 검증",
    "외부 HTTPS 전환과 서명·중복 방지 Webhook 수신 경로",
    "Ubuntu 24.04 · Activepieces 0.86.3 · 2026-07-31",
  ],
  2: [
    "결과: 외부 HTTPS와 서명 Webhook 경로가 검증되었습니다",
    "02",
    "HTTP 308 전환, 엄격한 Origin TLS, HMAC·Timestamp·중복 방지를 재시작과 재부팅 이후까지 확인했습니다.",
    "외부 경로",
    "HTTPS UI 200\nHTTP 308\nTLS verify PASS",
    "Webhook 판정",
    "Accepted 202\nDuplicate 409\nInvalid·Stale 401",
    "최종 결과",
    "6 Services Healthy  |  Worker Polling Ready  |  Reboot Recovery PASS",
  ],
  3: [
    "외부 Edge와 내부 실행 경로를 분리했습니다",
    "03",
    "Cloudflare는 HTTPS와 호스트 정책을, Gateway는 이벤트 신뢰 검증을, Activepieces는 Flow 실행을 담당합니다.",
    "01",
    "Cloudflare·Origin",
    "HTTP 308\nFull (strict)\n유효한 Origin TLS\n호스트 범위 제한",
    "02",
    "Ingress·Gateway",
    "경로 분기\nHMAC-SHA256\nTimestamp 300초\nRedis 중복 방지",
    "03",
    "Activepieces Runtime",
    "App 공개 기준 URL\nWorker 내부 URL\n6 Services Healthy\nDB·Redis 비공개",
    "배포 자산  |  Compose · Caddyfile · Gateway · 3개 운영 스크립트 · Runbook",
  ],
  4: [
    "서명·중복·실패 정책을 명시적으로 고정",
    "04",
    "정상 이벤트뿐 아니라 위조, 재전송, 오래된 요청과 상태 저장소 장애의 판정 규칙을 코드로 구현했습니다.",
    "Secret 값은 서버 .env 0600에만 존재하며 보고서·로그·저장소에는 포함하지 않습니다.",
  ],
  5: [
    "설정부터 복구까지 하나의 Runbook으로 반복",
    "05",
    "호스트 한정 Edge 규칙과 서버 배포 자산을 함께 관리하고 각 단계에 성공 판정을 둡니다.",
    "A",
    "Edge 설정",
    "Cloudflare",
    "308 · Full strict · Host scope",
    "B",
    "서버 구성",
    "configure",
    "URL · Gateway · Secret 생성",
    "C",
    "Compose 배포",
    "6 Services",
    "Build · Health · Polling",
    "D",
    "Webhook 검증",
    "5 Cases",
    "202 · 409 · 401 · 401 · 400",
    "E",
    "복구 검증",
    "Restart",
    "Ingress · Gateway 재검증",
    "F",
    "호스트 복구",
    "Reboot",
    "전체 서비스 · HTTPS · Webhook",
  ],
  6: [
    "검증 전 이벤트는 Activepieces에 도달하지 않습니다",
    "06",
    "Edge에서 HTTPS를 보장하고 Gateway가 신뢰를 판정한 신규 이벤트만 선택적 Upstream으로 전달합니다.",
    "외부 요청",
    "GitHub · Community\nMessenger Webhook\nHTTPS only",
    "Cloudflare",
    "308 Redirect\nFull (strict)\nHost-scoped rules",
    "Event Gateway",
    "Timestamp · HMAC\nRedis SET NX EX",
    "Activepieces",
    "검증 완료 이벤트\n시각적 Flow 실행",
    "Decision Gate",
    "202 / 400 / 401 / 409 / 503",
    "공개 TLS",
    "내부 실행",
  ],
  7: [
    "정상·거부·복구 시나리오를 실제 서버에서 통과",
    "07",
    "V1–4",
    "외부 경로",
    "HTTP 308\nHTTPS·Health 200\nTLS verify PASS\nSigned event 202",
    "V5–8",
    "거부 판정",
    "Duplicate 409\nInvalid 401\nStale 401\nMissing 400",
    "V9-V12",
    "내구성",
    "Unit 4/4\nRestart PASS\nReboot PASS\nSecret leaks 0",
    "외부 경로",
    "거부 정책",
    "복구·보안",
  ],
  8: [
    "구현과 운영 증적을 일관된 자산으로 관리",
    "08",
    "다음 운영자가 동일한 설정·검증·복구를 수행할 수 있도록 실행 코드와 문서, 구조화 증적을 함께 제공합니다.",
    "실행 자산",
    "Compose · Caddyfile\nGateway · Unit Tests\nConfigure · Verify Scripts\n서버 파일 Hash 일치",
    "운영 문서",
    "HTTPS·Webhook Runbook\n환경 기준선 갱신\n완료 보고서\n롤백·장애 분석",
    "검증 증적",
    "구조화 JSON\nPDF 보고서 · PPTX\nSHA-256 Manifest\n시각·Overflow 검사",
    "보안 기준  |  Secret 미커밋 · 요청 Body/서명 미로그 · DB/Redis 비공개 · Gateway Fail Closed",
  ],
  9: [
    "신뢰 경로 다음에는 Secret 수명주기와 첫 업무 Flow",
    "09",
    "Issue #14로 외부 이벤트 수신 기반을 확보했습니다. 다음 단계는 Secret 운영 통제 후 GitHub PR Merge Flow를 실증하는 것입니다.",
    "1",
    "2",
    "3",
    "4",
    "Secret",
    "#15 저장\n교체 · 폐기",
    "Backup",
    "#16 DB·Redis\n복구 훈련",
    "Observe",
    "#17 로그·메트릭\n#18 버전 정책",
    "First Flow",
    "#19 GitHub PR\nMerge Webhook",
    "Issue #14 완료 기준 = Signed Webhook 202 + 거부 정책 + 재시작·재부팅 복구 + 운영 자산화",
  ],
  10: [
    "최종 결과",
    "외부 HTTPS와\n신뢰 가능한 이벤트 경로를 확보했습니다.",
    "ISSUE #14",
    "VALIDATED · HTTPS 200 · HTTP 308 · SIGNED WEBHOOK 202 · REBOOT PASS",
    "ABLESTACK TechFlow · Secure Event Ingress",
    "Issue #14 · 2026-07-31",
  ],
};

const tableRows = [
  ["판정", "구현", "정상 응답", "실패 정책"],
  ["HTTPS", "Cloudflare + Origin", "200", "TLS 검증 실패"],
  ["HTTP", "Host Redirect Rule", "308", "경로·쿼리 보존"],
  ["서명", "HMAC-SHA256", "202", "401"],
  ["Timestamp", "허용차 300초", "202", "401"],
  ["중복", "Redis SET NX EX", "202", "409"],
  ["상태 저장소", "Redis 인증", "202", "503 Fail Closed"],
  ["Body", "최대 1 MiB", "202", "크기 초과 거부"],
  ["로그", "ID·상태만 기록", "leaks 0", "Body·Secret 미기록"],
];

const notesBySlide = {
  1: "Issue #14는 외부 HTTPS 전환과 신뢰 가능한 Webhook 수신 경로를 실서버에 구현하고 검증한 작업입니다.",
  2: "완료 판정은 HTTPS 응답뿐 아니라 서명 수락, 중복·위조 거부와 재부팅 복구를 포함합니다.",
  3: "Cloudflare, Origin, Caddy, Event Gateway와 Activepieces의 책임을 홉별로 분리했습니다.",
  4: "Webhook 판정 계약은 HMAC-SHA256, 300초 시각차와 Redis 기반 24시간 중복 방지입니다.",
  5: "Edge 설정부터 서버 재부팅 복구까지 동일 Runbook으로 반복할 수 있습니다.",
  6: "Gateway에서 검증하기 전 요청은 Activepieces Flow에 전달되지 않습니다.",
  7: "정상, 거부, 단위, 재시작, 재부팅과 비밀정보 노출 검사를 모두 통과했습니다.",
  8: "코드, Runbook, JSON, PDF, PPTX와 Manifest를 하나의 일관된 검증 자산으로 관리합니다.",
  9: "다음 단계는 Secret 수명주기와 백업·관측 기반을 보완한 뒤 첫 GitHub 업무 Flow를 실증하는 것입니다.",
  10: "Issue #14는 외부 이벤트를 안전하게 받을 수 있는 검증된 Ingress 기반을 확보한 상태로 종료합니다.",
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
        "- docs/decisions/https-webhook-ingress.json",
        "- docs/reports/issue-14-https-webhook-validation.md",
        "- docs/runbooks/https-webhook-ingress.md",
        "- https://github.com/ablecloud-team/ablestack-techflow/issues/14",
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
