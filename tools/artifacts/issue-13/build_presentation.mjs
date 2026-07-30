import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const ROOT = process.argv[2]
  ? path.resolve(process.argv[2])
  : path.resolve(process.cwd(), "../../..");
const TMP = `${ROOT}/tmp/artifacts/issue-13`;
const STARTER = `${TMP}/template-starter.pptx`;
const OUTPUT = `${ROOT}/output/presentation/activepieces-compose-deployment.pptx`;
const RENDER_DIR = `${TMP}/final-rendered`;
const LAYOUT_DIR = `${TMP}/final-layout`;
const INSPECT_OUTPUT = `${OUTPUT}.inspect.ndjson`;

const slideTexts = {
  1: [
    "ABLESTACK TECHFLOW · ISSUE #13",
    "Activepieces Compose\n배포 검증",
    "재현 가능한 사내 실증 실행 기반을 서버에 구축",
    "Ubuntu 24.04 · Activepieces 0.86.3 · 2026-07-30",
  ],
  2: [
    "결과: 네 서비스와 운영 절차가 검증되었다",
    "02",
    "사설망에 App·Worker·PostgreSQL·Redis를 배포하고 영속성과 서버 재부팅 복구를 확인했다.",
    "실행 기준선",
    "Activepieces 0.86.3\nWorker concurrency = 1\nPrivate HTTP :8080",
    "운영 기준선",
    "Docker 29.6.2\nCompose 5.3.1\nrestart: unless-stopped",
    "검증 결과",
    "Health 4/4  |  HTTP 200  |  Worker Polling Ready  |  Reboot Recovery PASS",
  ],
  3: [
    "실증 실행 기반을 네 서비스로 분리",
    "03",
    "App과 Worker를 분리하고 데이터와 큐는 호스트에 공개하지 않는 내부 네트워크로 구성했다.",
    "01",
    "Activepieces App",
    "UI · API · Webhook\n172.16.0.231:8080\nHealth API\n사설 주소만 바인딩",
    "02",
    "Activepieces Worker",
    "Flow 실행\nconcurrency = 1\nSocket.IO 연결\nPolling 준비 확인",
    "03",
    "PostgreSQL · Redis",
    "pgvector 0.8.0-pg14\nRedis 7.0.7 · AOF\n인증 사용\n호스트 포트 비공개",
    "배포 자산  |  Compose · 환경 계약 · 7개 운영 스크립트 · Runbook",
  ],
  4: [
    "버전·Health·영속성을 명시적으로 고정",
    "04",
    "latest 태그와 암묵적 상태 판정을 피하고 서비스별 운영 계약을 기록했다.",
    "Observed Digest는 JSON 증적에 보관 · 정식 Pinning 정책은 Issue #18",
  ],
  5: [
    "설치부터 복구까지 하나의 Runbook으로 반복",
    "05",
    "서버 배포 과정 자체를 명령·판정·복구 기준이 있는 운영 자산으로 만들었다.",
    "A",
    "사전 점검",
    "서버",
    "OS · CPU · RAM · Disk · Port",
    "B",
    "Docker 설치",
    "공식 저장소",
    "Engine · Compose · 자동 시작",
    "C",
    "환경 생성",
    "서버 로컬",
    ".env 0600 · 비밀값 미출력",
    "D",
    "Compose 배포",
    "순차 기동",
    "DB · Redis → App → Worker",
    "E",
    "검증",
    "통합 Health",
    "HTTP · Polling · Persistence",
    "F",
    "복구",
    "재부팅",
    "Docker · 4 Services 자동 복구",
  ],
  6: [
    "외부 노출 없이 내부 실행 경로를 우선 검증",
    "06",
    "App만 사설 주소에 바인딩하고 Worker와 데이터 계층은 Compose 내부 경로로 연결했다.",
    "접속",
    "사설망 사용자\n172.16.0.231:8080\nHTTP 200",
    "Activepieces App",
    "UI · API · Health\nSTRICT network mode\nTelemetry disabled",
    "Worker",
    "Socket.IO 연결\nPolling concurrency 1",
    "PostgreSQL · Redis",
    "내부 Compose network\n인증 · 영속 볼륨",
    "Health Gate",
    "4 Services + HTTP + Polling",
    "사설 바인딩",
    "내부 데이터 계층",
  ],
  7: [
    "영속성과 재부팅 복구를 실제 서버에서 통과",
    "07",
    "V7",
    "데이터 영속성",
    "PostgreSQL 공개 테이블 수\nRedis AOF Probe\n서비스 재시작 전후 비교\nPASS",
    "V8",
    "호스트 복구",
    "서버 재부팅\nDocker 자동 시작\n4 Services healthy\nHTTP 200",
    "V9–V10",
    "준비 후 품질",
    "Worker Polling Ready\n오류 0 · 경고 0\n비밀값 로그 노출 0\nPASS",
    "DB 유지",
    "자동 복구",
    "운영 준비 확인",
  ],
  8: [
    "배포 절차를 코드·문서·증적으로 자산화",
    "08",
    "실서버 경험이 사람의 기억이 아니라 저장소에서 재생성되는 운영 자산으로 남는다.",
    "배포 코드",
    "Compose · .env.example\nDocker 설치 · 환경 생성\n배포 · Health · 상태\n영속성 · 안전한 제거",
    "운영 문서",
    "전체 배포 Runbook\n서버 환경 기준선\n검증 보고서\n초기 관리자 생성 절차",
    "검증 증적",
    "구조화 JSON\nPDF 보고서 · PPTX\nSHA-256 Manifest\n실서버 파일 일치성",
    "안전 기준  |  .env 미커밋 · 데이터 제거 명시 승인 · DB/Redis 포트 비공개 · no-new-privileges",
  ],
  9: [
    "실행 기반 위에서 운영 품질과 첫 자동화를 연결",
    "09",
    "Issue #14부터 노출·비밀·복구·관측·버전 정책을 보강한 뒤 첫 GitHub Flow를 실증한다.",
    "1",
    "2",
    "3",
    "4",
    "외부 경로",
    "#14 HTTPS\nWebhook 서명",
    "비밀·복구",
    "#15 Secret\n#16 Backup",
    "운영 품질",
    "#17 Observability\n#18 Version",
    "첫 Flow",
    "#19 GitHub PR\nMerge Webhook",
    "Issue #13 완료 기준은 배포 성공뿐 아니라 재현 가능한 자산·영속성·재부팅 복구 증적까지 포함",
  ],
  10: [
    "최종 결과",
    "배포가 아니라,\n재현 가능한 운영 기반을 확보했다.",
    "ISSUE #13",
    "VALIDATED · 4 Services Healthy · Persistence PASS · Reboot Recovery PASS",
    "ABLESTACK TechFlow · Activepieces Runtime",
    "Issue #13 · 2026-07-30",
  ],
};

const tableRows = [
  ["서비스", "이미지", "Health", "영속성"],
  ["App", "activepieces:0.86.3", "API health", "cache_data"],
  ["Worker", "activepieces:0.86.3", "health + polling", "shared cache"],
  ["PostgreSQL", "pgvector:0.8.0-pg14", "pg_isready", "postgres_data"],
  ["Redis", "redis:7.0.7", "authenticated PING", "redis_data + AOF"],
  ["HTTP", "172.16.0.231:8080", "200 Healthy", "private bind"],
  ["Execution", "SANDBOX\nCODE_ONLY", "worker ready", "concurrency 1"],
  ["Network", "STRICT", "internal data path", "DB ports closed"],
  ["Restart", "unless-stopped", "post-reboot pass", "volumes retained"],
];

const notesBySlide = {
  1: "Issue #13은 Activepieces 사내 실증 실행 기반을 실제 서버에 구축하고 검증한 작업이다.",
  2: "네 서비스 Health, HTTP, Worker Polling과 재부팅 복구를 완료 기준으로 사용했다.",
  3: "App과 Worker를 분리하고 PostgreSQL과 Redis는 내부 네트워크에만 배치했다.",
  4: "버전과 Health, 영속성 계약을 명시하고 관측 Digest를 구조화 기록에 보관했다.",
  5: "사전 점검부터 재부팅 복구까지 동일 Runbook으로 반복할 수 있다.",
  6: "현재 App은 사설 주소에만 노출하며 외부 HTTPS와 Webhook은 Issue #14 범위다.",
  7: "서비스 재시작과 호스트 재부팅 뒤 데이터와 실행 준비 상태가 복구됨을 확인했다.",
  8: "Compose, 스크립트, Runbook, JSON, PDF와 Manifest를 하나의 자산 체계로 관리한다.",
  9: "후속 이슈는 외부 경로, 비밀정보, 백업, 관측, 버전과 첫 업무 Flow 순서다.",
  10: "Issue #13은 재현 가능한 배포와 운영 검증 기반을 확보한 상태로 완료한다.",
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
        "- docs/decisions/activepieces-compose-deployment.json",
        "- docs/reports/issue-13-activepieces-compose-deployment-validation.md",
        "- docs/runbooks/activepieces-compose-deployment.md",
        "- https://github.com/ablecloud-team/ablestack-techflow/issues/13",
        "- https://www.activepieces.com/docs/install/options/docker-compose",
        "- https://www.activepieces.com/docs/install/architecture/workers",
        "- https://docs.docker.com/engine/install/ubuntu/",
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
