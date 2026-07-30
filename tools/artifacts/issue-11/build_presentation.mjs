import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import {
  Presentation,
  PresentationFile,
  layers,
  shape,
  table,
  text,
} from "@oai/artifact-tool";

const root = path.resolve(process.argv[2] ?? ".");
const dataPath = path.join(root, "docs", "decisions", "activepieces-license-review.json");
const outputPath = path.join(root, "output", "presentation", "activepieces-license-review.pptx");
const data = JSON.parse(fs.readFileSync(dataPath, "utf8"));

const W = 1280;
const H = 720;
const C = {
  black: "#111111",
  gray900: "#252525",
  gray700: "#555555",
  gray500: "#858585",
  gray300: "#D9D9D9",
  gray100: "#F2F2F2",
  paleBlue: "#F3FAFE",
  lightBlue: "#DDF3FF",
  accent: "#6DCBF4",
  blue: "#3D8DFF",
  green: "#177245",
  greenBg: "#E8F5ED",
  amber: "#8A5A00",
  amberBg: "#FFF4D6",
  red: "#A52714",
  redBg: "#FCE8E6",
  white: "#FFFFFF",
};
const FONT = "Malgun Gothic";

const presentation = Presentation.create({ slideSize: { width: W, height: H } });

function t(value, left, top, width, height, fontSize = 24, options = {}) {
  return text([value], {
    position: { left, top },
    width,
    height,
    style: {
      fontSize: `${fontSize}px`,
      typeface: FONT,
      color: options.color ?? C.black,
      alignment: options.alignment ?? "left",
      verticalAlignment: options.verticalAlignment ?? "top",
      autoFit: "shrinkText",
      fontWeight: options.bold ? "700" : "400",
      insets: options.insets ?? { top: 0, right: 0, bottom: 0, left: 0 },
    },
  });
}

function box(left, top, width, height, fill = C.gray100, radius = true, stroke = null) {
  return shape({
    geometry: radius ? "roundRect" : "rect",
    fill,
    stroke: stroke ? { fill: stroke, width: 1 } : undefined,
    position: { left, top },
    width,
    height,
  });
}

function line(left, top, width, height, fill = C.gray300) {
  return shape({
    geometry: "rect",
    fill,
    position: { left, top },
    width,
    height,
  });
}

function slideTitle(title, number, subtitle = "") {
  const parts = [
    t(title, 42, 34, 1120, 62, 39, { bold: true }),
    t(String(number).padStart(2, "0"), 1180, 657, 58, 24, 14, {
      alignment: "right",
      color: C.gray500,
    }),
  ];
  if (subtitle) {
    parts.push(t(subtitle, 42, 101, 1170, 52, 21, { color: C.gray700 }));
  }
  return parts;
}

function addSlide(elements, notes) {
  const slide = presentation.slides.add();
  slide.compose(
    layers({ width: "fill", height: "fill" }, elements),
    { frame: { left: 0, top: 0, width: W, height: H }, baseUnit: 1 },
  );
  slide.speakerNotes.textFrame.setText(notes);
  slide.speakerNotes.setVisible(true);
  return slide;
}

function notes(...urls) {
  return [
    "핵심 메시지와 의사결정 조건을 설명한다.",
    "[Sources]",
    ...urls.map((url) => `- ${url}`),
    "[/Sources]",
  ].join("\n");
}

function badge(label, left, top, width, status) {
  const palette =
    status === "ok"
      ? [C.greenBg, C.green]
      : status === "conditional"
        ? [C.amberBg, C.amber]
        : [C.redBg, C.red];
  return [
    box(left, top, width, 42, palette[0], true, palette[1]),
    t(label, left + 8, top + 8, width - 16, 26, 17, {
      bold: true,
      color: palette[1],
      alignment: "center",
    }),
  ];
}

// 1. Cover — Codex Grid slide-01 hierarchy.
addSlide(
  [
    t("ABLESTACK TECHFLOW · ISSUE #11", 42, 41, 700, 36, 24, { bold: true }),
    t("Activepieces\n기능·라이선스 검토", 42, 190, 1040, 210, 73, { bold: true }),
    t("Community 실행 기반과 상위 기능 자체 구현 원칙", 42, 493, 860, 72, 27, {
      color: C.gray700,
    }),
    line(42, 620, 1196, 3, C.blue),
    t(`기준 ${data.baseline.version} · ${data.analysisDate}`, 42, 640, 500, 30, 16, {
      color: C.gray500,
    }),
  ],
  notes(
    "https://github.com/activepieces/activepieces/releases/tag/0.86.3",
    "https://github.com/activepieces/activepieces/blob/0.86.3/LICENSE",
  ),
);

// 2. Decision summary — Codex Grid slide-11 comparison.
addSlide(
  [
    ...slideTitle("결론: Community를 기반으로 필요한 기능을 직접 구현", 2),
    t(
      "Activepieces의 네이티브 기능 분류는 참고정보이며 TechFlow의 자체 구현 범위를 제한하지 않는다.",
      42,
      122,
      1170,
      64,
      23,
      { color: C.gray700 },
    ),
    box(42, 228, 572, 192, C.greenBg, true),
    t("기본 실행 엔진", 72, 257, 510, 39, 29, { bold: true, color: C.green }),
    t("Activepieces Community 0.86.3\nBuilder · Webhook · Custom Piece\nQueue · Worker · 실행·재시도", 72, 311, 500, 90, 21),
    box(656, 228, 582, 192, C.lightBlue, true),
    t("자체 구현 범위", 687, 257, 520, 39, 29, { bold: true, color: C.blue }),
    t("TechFlow API · Builder · SSO/RBAC/Audit\nSecret · Template · GitOps · Worker 격리\n고객 공개 여부와 무관하게 구현 가능", 687, 311, 510, 90, 21),
    box(42, 467, 1196, 130, C.lightBlue, true),
    t("제품 원칙", 72, 492, 160, 32, 23, { bold: true, color: C.blue }),
    t(
      "TechFlow Core = 제품 권한·정책·감사  |  Activepieces = 시각적 실행 엔진  |  ABLESTACK API = 실제 자원 작업",
      72,
      536,
      1126,
      39,
      21,
      { bold: true },
    ),
  ],
  notes(
    "https://github.com/activepieces/activepieces/blob/0.86.3/LICENSE",
    "https://www.activepieces.com/docs/endpoints/overview",
    "https://www.activepieces.com/docs/embedding/configure-embedding",
  ),
);

// 3. Evidence boundary.
addSlide(
  [
    ...slideTitle(
      "하나의 저장소, 세 개의 권리 경계",
      3,
      "라이선스 경계는 네이티브 코드 사용 조건이며 자체 기능 구현의 제한선이 아니다.",
    ),
    box(42, 192, 360, 338, C.greenBg, true),
    t("01", 72, 218, 70, 56, 42, { bold: true, color: C.green }),
    t("MIT 영역", 72, 282, 280, 39, 29, { bold: true }),
    t("EE 경로 밖의 Activepieces 자체 코드\n\n상용 사용·수정·배포 가능\n저작권·허가 고지 유지", 72, 338, 286, 150, 20),
    box(460, 192, 360, 338, C.redBg, true),
    t("02", 490, 218, 70, 56, 42, { bold: true, color: C.red }),
    t("Enterprise 영역", 490, 282, 280, 39, 29, { bold: true }),
    t("packages/ee/**\nserver/api/src/app/ee/**\n\n운영 사용은 유효한 계약·좌석 필요", 490, 338, 286, 150, 20),
    box(878, 192, 360, 338, C.amberBg, true),
    t("03", 908, 218, 70, 56, 42, { bold: true, color: C.amber }),
    t("제3자 구성요소", 908, 282, 280, 39, 29, { bold: true }),
    t("라이브러리 · Piece 의존성\n컨테이너 OS·도구\n\n최종 이미지 SBOM·NOTICE 필요", 908, 338, 286, 150, 20),
    t(
      `고정 증거  |  tag ${data.baseline.version}  ·  commit ${data.baseline.tagCommit.slice(0, 12)}…`,
      42,
      580,
      920,
      34,
      17,
      { color: C.gray700 },
    ),
  ],
  notes(
    "https://github.com/activepieces/activepieces/blob/0.86.3/LICENSE",
    "https://github.com/activepieces/activepieces/blob/0.86.3/packages/ee/LICENSE",
  ),
);

// 4. Feature matrix summary — Codex Grid slide-14 table.
const matrixValues = [
  ["기능군", "Community 기반", "제품 구현", "TechFlow 방향"],
  ["Builder·Webhook·실행", "기본 사용", "확장", "Event Gateway"],
  ["Custom Piece", "기본 사용", "확장", "표준 연동 경로"],
  ["제품 API", "별도 구현", "자체 구현", "TechFlow API·Webhook"],
  ["SSO·RBAC·SCIM", "별도 구현", "자체 구현", "TechFlow IAM·RBAC"],
  ["Audit·Event Stream", "별도 구현", "자체 구현", "TechFlow 감사·이벤트"],
  ["Secret·Connection", "별도 구현", "자체 구현", "Secret Broker"],
  ["Builder·Branding", "별도 구현", "자체 구현", "TechFlow Portal"],
  ["Git·Template·Worker 격리", "별도 구현", "자체 구현", "GitOps·Worker Pool"],
];
addSlide(
  [
    ...slideTitle("기능 매트릭스: Community 위에 제품 기능을 자유롭게 확장", 4),
    t(
      "공식 문서와 0.86.3 소스의 Edition 분기·feature flag를 함께 확인했다.",
      42,
      112,
      1170,
      40,
      20,
      { color: C.gray700 },
    ),
    table({
      rows: matrixValues.length,
      columns: 4,
      values: matrixValues,
      columnWidths: [320, 220, 220, 437],
      position: { left: 42, top: 180 },
      width: 1197,
      height: 425,
    }),
    t("전체 23개 행은 JSON 원본과 의사결정 문서에서 관리", 42, 625, 660, 28, 16, {
      color: C.gray500,
    }),
  ],
  notes(
    "https://www.activepieces.com/docs/endpoints/overview",
    "https://www.activepieces.com/docs/admin-guide/guides/sso",
    "https://www.activepieces.com/docs/admin-guide/guides/permissions",
    "https://www.activepieces.com/docs/admin-guide/security/audit-logs/overview",
  ),
);

// 5. Scenarios.
const scenarioRows = [
  ["A", "사내 Assist PoC", "승인", "ok"],
  ["B", "고객 전용 인스턴스", "구현 가능", "ok"],
  ["C", "고객용 구성·관리 UI", "자체 구현", "ok"],
  ["D", "TechFlow Builder", "자체 구현", "ok"],
  ["E", "다중 고객 플랫폼", "자체 구현", "ok"],
  ["F", "오프라인 배포 기능", "자체 구현", "ok"],
];
const scenarioElements = [
  ...slideTitle("모든 제품 시나리오는 구현 가능", 5, "고객 공개 여부는 구현 판정과 분리하고 제품 책임자가 결정한다."),
];
scenarioRows.forEach((row, index) => {
  const col = index % 2;
  const r = Math.floor(index / 2);
  const left = col === 0 ? 42 : 656;
  const top = 185 + r * 145;
  const bg = row[3] === "ok" ? C.greenBg : row[3] === "conditional" ? C.amberBg : C.redBg;
  const fg = row[3] === "ok" ? C.green : row[3] === "conditional" ? C.amber : C.red;
  scenarioElements.push(
    box(left, top, 582, 111, bg, true),
    t(row[0], left + 24, top + 22, 58, 48, 38, { bold: true, color: fg }),
    t(row[1], left + 94, top + 22, 310, 35, 23, { bold: true }),
    t(row[2], left + 402, top + 24, 150, 31, 18, {
      bold: true,
      alignment: "right",
      color: fg,
    }),
    t(
      index === 0
        ? "Community 기반으로 즉시 진행"
        : index === 1
          ? "배포·관리 기능까지 자체 구현"
          : index === 5
            ? "설치·업그레이드·운영 기능 구현"
            : "TechFlow 제품 기능으로 자체 구현",
      left + 94,
      top + 67,
      450,
      27,
      16,
      { color: C.gray700 },
    ),
  );
});
addSlide(
  scenarioElements,
  notes(
    "https://www.activepieces.com/terms",
    "https://www.activepieces.com/docs/embedding/configure-embedding",
  ),
);

// 6. Architecture — connectors deliberately placed before nodes.
addSlide(
  [
    ...slideTitle(
      "권한과 실행을 분리한 목표 아키텍처",
      6,
      "Activepieces를 대체 불가능한 제품 코어가 아니라 교체 가능한 실행 계층으로 둔다.",
    ),
    line(253, 312, 98, 7, C.accent),
    line(612, 312, 98, 7, C.accent),
    line(968, 312, 98, 7, C.accent),
    line(792, 416, 7, 74, C.gray300),
    box(42, 244, 211, 144, C.gray100, true),
    t("채널", 67, 269, 160, 31, 21, { bold: true }),
    t("GitHub\nCommunity\nMessenger · Portal", 67, 312, 160, 62, 18),
    box(351, 224, 261, 184, C.lightBlue, true, C.blue),
    t("TechFlow Core", 378, 252, 207, 36, 26, { bold: true, color: C.blue }),
    t("인증 · 권한 · 정책 · 승인\n감사 · 템플릿 · API\nAI · RAG", 378, 309, 207, 76, 18),
    box(710, 244, 258, 144, C.paleBlue, true),
    t("Activepieces CE", 738, 269, 204, 31, 23, { bold: true }),
    t("Builder · Webhook\nQueue · Worker · Retry", 738, 320, 204, 58, 18),
    box(1066, 244, 172, 144, C.gray100, true),
    t("ABLESTACK", 1090, 269, 126, 31, 20, { bold: true }),
    t("권한 · 상태\n멱등성 · 작업", 1090, 320, 126, 58, 18),
    box(650, 490, 298, 92, C.greenBg, true),
    t("TechFlow Custom Pieces", 678, 512, 242, 29, 21, {
      bold: true,
      color: C.green,
      alignment: "center",
    }),
    t("서명 Webhook · Callback", 678, 548, 242, 24, 16, {
      alignment: "center",
      color: C.gray700,
    }),
    t("제품 권한", 390, 448, 160, 28, 17, { bold: true, color: C.blue }),
    t("실행 계층", 752, 448, 160, 28, 17, { bold: true, color: C.gray700 }),
  ],
  notes(
    "https://www.activepieces.com/docs/install/architecture/overview",
    "https://www.activepieces.com/docs/endpoints/overview",
  ),
);

// 7. Commercial gates.
addSlide(
  [
    ...slideTitle("구현 원칙: 라이선스와 공개 여부는 백로그 게이트가 아니다", 7),
    box(42, 174, 370, 376, C.greenBg, true),
    t("I1", 72, 202, 90, 58, 42, { bold: true, color: C.green }),
    t("Community 기반", 72, 274, 290, 40, 29, { bold: true }),
    t("시각적 설계·실행 엔진\nWebhook · Queue · Worker\nCustom Piece 연동\n고정 버전·운영 품질", 72, 338, 280, 132, 21),
    box(455, 174, 370, 376, C.lightBlue, true),
    t("I2", 485, 202, 90, 58, 42, { bold: true, color: C.blue }),
    t("상위 기능 자체 구현", 485, 274, 290, 40, 29, { bold: true }),
    t("Builder · 제품 API\nSSO · RBAC · Audit\nSecret · Template · GitOps\nWorker 격리 · Analytics", 485, 338, 280, 132, 21),
    box(868, 174, 370, 376, C.gray100, true),
    t("I3–I4", 898, 202, 160, 58, 42, { bold: true, color: C.gray700 }),
    t("결정 책임 분리", 898, 274, 290, 40, 29, { bold: true }),
    t("제품 권한은 TechFlow\n자원 권한은 ABLESTACK API\n고객 공개·판매·배포는\n제품 책임자가 별도 결정", 898, 338, 280, 132, 21),
    t("기본 실행 기반", 42, 586, 150, 30, 18, { bold: true, color: C.green }),
    line(201, 601, 210, 4, C.green),
    t("요구사항대로 구현", 455, 586, 170, 30, 18, { bold: true, color: C.blue }),
    line(634, 601, 190, 4, C.blue),
    t("공개 판단은 별도", 868, 586, 170, 30, 18, { bold: true, color: C.gray700 }),
    line(1047, 601, 190, 4, C.gray700),
  ],
  notes(
    "https://github.com/activepieces/activepieces/blob/0.86.3/packages/ee/LICENSE",
    "https://www.activepieces.com/terms",
  ),
);

// 8. Supply chain.
addSlide(
  [
    ...slideTitle(
      "공개·배포 조건은 구현 제약이 아닌 참고정보",
      8,
      "package.json만으로는 Piece·컨테이너 전체의 제3자 라이선스를 증명할 수 없다.",
    ),
    box(42, 188, 372, 310, C.redBg, true),
    t("확인 항목", 72, 218, 140, 36, 27, { bold: true, color: C.red }),
    t("공식 이미지에 EE 빌드 입력 포함\n결합 이미지 재배포 권리 미확정\n다수 패키지의 license 필드 부재\n상표·Powered by 조건 별도", 72, 282, 300, 156, 21),
    box(454, 188, 372, 310, C.lightBlue, true),
    t("필수 증적", 484, 218, 150, 36, 27, { bold: true, color: C.blue }),
    t("이미지 digest 고정\nSPDX/CycloneDX SBOM\nNOTICE·수동 예외 검토\n취약점·라이선스 결과 보관", 484, 282, 300, 156, 21),
    box(866, 188, 372, 310, C.greenBg, true),
    t("적용 원칙", 896, 218, 150, 36, 27, { bold: true, color: C.green }),
    t("정보는 보고서에 유지\n공개 결정 시 재검토\n자체 구현은 계속 진행\n백로그 게이트로 사용하지 않음", 896, 282, 300, 156, 21),
    box(42, 548, 1196, 70, C.gray100, true),
    t(
      "결정  |  라이선스·공개 관련 확인은 제품 책임자의 공개 판단을 지원하며 기능 구현을 차단하지 않는다.",
      72,
      568,
      1136,
      32,
      20,
      { bold: true },
    ),
  ],
  notes(
    "https://github.com/activepieces/activepieces/blob/0.86.3/LICENSE",
    "https://github.com/activepieces/activepieces/blob/0.86.3/packages/ee/LICENSE",
  ),
);

// 9. Actions — Codex Grid slide-17 timeline.
addSlide(
  [
    ...slideTitle("다음 실행 순서", 9, "Community 실행 기반 위에 TechFlow 제품 기능을 단계적으로 구현한다."),
    line(126, 332, 960, 6, C.gray300),
    box(84, 291, 84, 84, C.greenBg, true, C.green),
    t("1", 84, 306, 84, 50, 36, { bold: true, color: C.green, alignment: "center" }),
    box(396, 291, 84, 84, C.lightBlue, true, C.blue),
    t("2", 396, 306, 84, 50, 36, { bold: true, color: C.blue, alignment: "center" }),
    box(708, 291, 84, 84, C.amberBg, true, C.amber),
    t("3", 708, 306, 84, 50, 36, { bold: true, color: C.amber, alignment: "center" }),
    box(1020, 291, 84, 84, C.redBg, true, C.red),
    t("4", 1020, 306, 84, 50, 36, { bold: true, color: C.red, alignment: "center" }),
    t("CE 실행 환경", 42, 408, 170, 35, 23, { bold: true, alignment: "center" }),
    t("Builder · Webhook\nQueue · Worker", 42, 454, 170, 60, 18, { alignment: "center" }),
    t("TechFlow Core", 354, 408, 170, 35, 23, { bold: true, alignment: "center" }),
    t("정책 · 승인 · 감사\n제품 API", 354, 454, 170, 60, 18, { alignment: "center" }),
    t("제품 UI·통합", 666, 408, 170, 35, 23, { bold: true, alignment: "center" }),
    t("Portal · Builder\nIAM · Secret", 666, 454, 170, 60, 18, { alignment: "center" }),
    t("운영 고도화", 978, 408, 170, 35, 23, { bold: true, alignment: "center" }),
    t("GitOps · Worker 격리\nAnalytics · AIOps", 978, 454, 170, 60, 18, { alignment: "center" }),
    box(42, 570, 1196, 63, C.lightBlue, true),
    t(
      "즉시 실행: Activepieces CE 테스트 환경 구축 · 필요한 상위 기능은 제품 요구사항과 우선순위에 따라 자체 구현",
      72,
      589,
      1136,
      29,
      19,
      { bold: true },
    ),
  ],
  notes(
    "https://www.activepieces.com/docs/install/overview",
    "https://www.activepieces.com/docs/install/architecture/overview",
  ),
);

// 10. Closing — Codex Grid slide-26 spirit.
addSlide(
  [
    t("최종 권고", 42, 42, 800, 58, 39, { bold: true }),
    t("Community를 기반으로 구현하고,\n필요한 상위 기능은 TechFlow에서 만든다.", 42, 164, 1140, 176, 59, {
      bold: true,
    }),
    box(42, 395, 1196, 116, C.lightBlue, true),
    t("승인 요청", 72, 424, 170, 32, 22, { bold: true, color: C.blue }),
    t(
      "자체 구현 범위 제한 없음 · 고객 공개·판매·배포 결정은 제품 책임자에게 분리",
      72,
      467,
      1126,
      31,
      22,
      { bold: true },
    ),
    line(42, 603, 1196, 3, C.blue),
    t("ABLESTACK TechFlow · Issue #11", 42, 628, 500, 28, 16, { color: C.gray500 }),
    t(`${data.baseline.version} · ${data.analysisDate}`, 955, 628, 283, 28, 16, {
      color: C.gray500,
      alignment: "right",
    }),
  ],
  notes(
    "https://github.com/activepieces/activepieces/blob/0.86.3/LICENSE",
    "https://www.activepieces.com/terms",
  ),
);

fs.mkdirSync(path.dirname(outputPath), { recursive: true });
const file = await PresentationFile.exportPptx(presentation);
await file.save(outputPath);
console.log(outputPath);

export { presentation };

if (process.argv[1] && import.meta.url !== pathToFileURL(process.argv[1]).href) {
  // Module imported for diagnostics.
}
