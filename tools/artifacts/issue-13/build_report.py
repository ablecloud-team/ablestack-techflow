from __future__ import annotations

import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[3]
DATA_PATH = ROOT / "docs" / "decisions" / "activepieces-compose-deployment.json"
OUTPUT_PATH = ROOT / "output" / "pdf" / "activepieces-compose-deployment-report.pdf"

FONT = "MalgunGothic"
FONT_BOLD = "MalgunGothicBold"
pdfmetrics.registerFont(TTFont(FONT, "C:/Windows/Fonts/malgun.ttf"))
pdfmetrics.registerFont(TTFont(FONT_BOLD, "C:/Windows/Fonts/malgunbd.ttf"))

BLACK = colors.HexColor("#111111")
GRAY_700 = colors.HexColor("#4B5563")
GRAY_500 = colors.HexColor("#6B7280")
GRAY_300 = colors.HexColor("#D1D5DB")
GRAY_100 = colors.HexColor("#F3F4F6")
BLUE = colors.HexColor("#3B82F6")
PALE_BLUE = colors.HexColor("#EEF8FD")
GREEN = colors.HexColor("#117A4B")
PALE_GREEN = colors.HexColor("#E8F5EE")
AMBER = colors.HexColor("#8A5A00")
PALE_AMBER = colors.HexColor("#FFF3D6")

base_styles = getSampleStyleSheet()
styles = {
    "cover_meta": ParagraphStyle(
        "cover_meta",
        parent=base_styles["Normal"],
        fontName=FONT,
        fontSize=10,
        leading=14,
        textColor=GRAY_700,
    ),
    "title": ParagraphStyle(
        "title",
        parent=base_styles["Title"],
        fontName=FONT_BOLD,
        fontSize=28,
        leading=38,
        textColor=BLACK,
        alignment=TA_LEFT,
        spaceAfter=0,
    ),
    "subtitle": ParagraphStyle(
        "subtitle",
        parent=base_styles["Normal"],
        fontName=FONT,
        fontSize=14,
        leading=21,
        textColor=GRAY_700,
    ),
    "h1": ParagraphStyle(
        "h1",
        parent=base_styles["Heading1"],
        fontName=FONT_BOLD,
        fontSize=20,
        leading=27,
        textColor=BLACK,
        spaceAfter=6 * mm,
    ),
    "h2": ParagraphStyle(
        "h2",
        parent=base_styles["Heading2"],
        fontName=FONT_BOLD,
        fontSize=13,
        leading=19,
        textColor=BLACK,
        spaceBefore=4 * mm,
        spaceAfter=3 * mm,
    ),
    "body": ParagraphStyle(
        "body",
        parent=base_styles["BodyText"],
        fontName=FONT,
        fontSize=9.2,
        leading=14.5,
        textColor=colors.HexColor("#2F3136"),
        spaceAfter=2 * mm,
    ),
    "small": ParagraphStyle(
        "small",
        parent=base_styles["BodyText"],
        fontName=FONT,
        fontSize=7.4,
        leading=10.5,
        textColor=GRAY_500,
    ),
    "callout": ParagraphStyle(
        "callout",
        parent=base_styles["BodyText"],
        fontName=FONT_BOLD,
        fontSize=11.2,
        leading=17,
        textColor=BLACK,
    ),
    "table": ParagraphStyle(
        "table",
        parent=base_styles["BodyText"],
        fontName=FONT,
        fontSize=7.5,
        leading=10.5,
        textColor=colors.HexColor("#30343B"),
    ),
    "table_head": ParagraphStyle(
        "table_head",
        parent=base_styles["BodyText"],
        fontName=FONT_BOLD,
        fontSize=7.5,
        leading=10.5,
        textColor=colors.white,
    ),
    "badge": ParagraphStyle(
        "badge",
        parent=base_styles["BodyText"],
        fontName=FONT_BOLD,
        fontSize=8.5,
        leading=12,
        textColor=GREEN,
        alignment=TA_CENTER,
    ),
}


def p(text: object, style: str = "body") -> Paragraph:
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), styles[style])


def bullet(text: str) -> Paragraph:
    return Paragraph(
        f"• {escape(text)}",
        ParagraphStyle(
            "bullet_local",
            parent=styles["body"],
            leftIndent=4 * mm,
            firstLineIndent=-3 * mm,
            spaceAfter=2 * mm,
        ),
    )


def make_table(
    rows: list[list[object]],
    widths: list[float],
    *,
    header: bool = True,
    font_size: float = 7.5,
) -> Table:
    body_style = ParagraphStyle(
        f"table_{font_size}",
        parent=styles["table"],
        fontSize=font_size,
        leading=font_size * 1.42,
    )
    converted: list[list[Paragraph]] = []
    for row_index, row in enumerate(rows):
        style = styles["table_head"] if header and row_index == 0 else body_style
        converted.append(
            [Paragraph(escape(str(value)).replace("\n", "<br/>"), style) for value in row]
        )
    result = Table(converted, colWidths=widths, repeatRows=1 if header else 0)
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.35, GRAY_300),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        commands.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BLACK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ]
        )
        start = 1
    else:
        start = 0
    for row_index in range(start, len(rows)):
        if row_index % 2 == 0:
            commands.append(("BACKGROUND", (0, row_index), (-1, row_index), PALE_BLUE))
    result.setStyle(TableStyle(commands))
    return result


def callout(text: str, *, color=PALE_GREEN, text_color=GREEN) -> Table:
    box = Table([[p(text, "callout")]], colWidths=[170 * mm])
    box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), color),
                ("BOX", (0, 0), (-1, -1), 0.7, text_color),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return box


class DeploymentDocument(BaseDocTemplate):
    def __init__(self, filename: str):
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=21 * mm,
            bottomMargin=18 * mm,
            title="Activepieces Compose 배포 검증 보고서",
            author="ABLESTACK TechFlow",
            subject="GitHub Issue #13",
        )
        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="normal",
        )
        self.addPageTemplates(PageTemplate(id="all", frames=frame, onPage=self._page))

    def _page(self, canvas, doc):
        if doc.page <= 1:
            return
        canvas.saveState()
        canvas.setStrokeColor(GRAY_300)
        canvas.setLineWidth(0.4)
        canvas.line(18 * mm, A4[1] - 14 * mm, A4[0] - 18 * mm, A4[1] - 14 * mm)
        canvas.setFont(FONT, 7)
        canvas.setFillColor(GRAY_500)
        canvas.drawString(
            18 * mm,
            A4[1] - 11 * mm,
            "ABLESTACK TechFlow · Activepieces Compose · Issue #13",
        )
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"{doc.page}")
        canvas.restoreState()


def build() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc = DeploymentDocument(str(OUTPUT_PATH))
    story: list[object] = []

    # 1. Cover
    story.extend(
        [
            Spacer(1, 22 * mm),
            p("ABLESTACK TECHFLOW", "cover_meta"),
            Spacer(1, 6 * mm),
            p("Activepieces Compose\n배포 검증 보고서", "title"),
            Spacer(1, 7 * mm),
            p("사내 업무 자동화 실증을 위한 재현 가능한 실행 기반", "subtitle"),
            Spacer(1, 22 * mm),
            callout(
                "VALIDATED · 4개 서비스 Healthy · HTTP 200 · 영속성 PASS · 서버 재부팅 복구 PASS"
            ),
            Spacer(1, 30 * mm),
            make_table(
                [
                    ["항목", "값"],
                    ["GitHub Issue", "#13 Activepieces 테스트 서버 Docker Compose 구성"],
                    ["검증일", data["validatedAt"]],
                    ["대상", f'{data["target"]["hostname"]} · {data["target"]["operatingSystem"]}'],
                    ["배포 경로", data["target"]["deploymentPath"]],
                    ["문서 상태", data["status"].upper()],
                ],
                [40 * mm, 130 * mm],
            ),
            Spacer(1, 9 * mm),
            p(
                "이 보고서에는 비밀번호, API Key, JWT Secret, 암호화 키 및 서버의 실제 .env 값이 포함되지 않는다.",
                "small",
            ),
            PageBreak(),
        ]
    )

    # 2. Result summary
    story.extend(
        [
            p("1. 배포 결과 요약", "h1"),
            callout(
                "Issue #13의 완료 기준은 컨테이너 기동이 아니라 재현 가능한 배포 자산, 통합 Health, 데이터 영속성 및 호스트 재부팅 복구다."
            ),
            Spacer(1, 6 * mm),
            p("검증 대상", "h2"),
            make_table(
                [
                    ["항목", "검증값"],
                    ["운영체제", data["target"]["operatingSystem"]],
                    ["CPU / Memory / Swap", f'{data["target"]["cpu"]} / {data["target"]["memory"]} / {data["target"]["swap"]}'],
                    ["Docker", data["runtime"]["dockerEngine"]],
                    ["Docker Compose", data["runtime"]["dockerCompose"]],
                    ["사설 접속 URL", data["target"]["privateUrl"]],
                    ["배포 경로", data["target"]["deploymentPath"]],
                ],
                [52 * mm, 118 * mm],
            ),
            p("핵심 결과", "h2"),
            make_table(
                [
                    ["확인 항목"],
                    ["App, Worker, PostgreSQL, Redis 네 서비스를 모두 healthy 상태로 확인했다."],
                    ["Activepieces Health API와 UI 응답을 HTTP 200으로 확인했다."],
                    ["Worker가 App에 연결되고 concurrency=1 Polling을 시작한 상태를 확인했다."],
                    ["PostgreSQL과 Redis 데이터를 서비스 재시작 전후에 비교해 영속성을 확인했다."],
                    ["서버 재부팅 뒤 Docker와 네 컨테이너가 자동 복구되는 것을 확인했다."],
                ],
                [170 * mm],
                font_size=7.8,
            ),
            PageBreak(),
        ]
    )

    # 3. Architecture
    services = {service["name"]: service for service in data["services"]}
    story.extend(
        [
            p("2. 배포 아키텍처", "h1"),
            p(
                "단일 Ubuntu 서버에서 App과 Worker를 분리하고 PostgreSQL과 Redis는 Compose 내부 네트워크에만 배치했다. App만 사설 주소에 바인딩한다."
            ),
            make_table(
                [
                    ["사설 사용자", "Activepieces App", "Worker", "데이터 계층"],
                    [
                        "172.16.0.231:8080",
                        "UI · API · Webhook\nHealth API",
                        "Flow 실행\nPolling concurrency 1",
                        "PostgreSQL · Redis\nHost port 비공개",
                    ],
                ],
                [39 * mm, 44 * mm, 42 * mm, 45 * mm],
            ),
            p("서비스 구성", "h2"),
            make_table(
                [
                    ["서비스", "이미지", "Health / 준비", "영속성"],
                    [
                        "App",
                        services["app"]["image"],
                        services["app"]["health"],
                        "cache_data",
                    ],
                    [
                        "Worker",
                        services["worker"]["image"],
                        f'{services["worker"]["health"]} / polling {services["worker"]["polling"]}',
                        "shared cache",
                    ],
                    [
                        "PostgreSQL",
                        services["postgres"]["image"],
                        services["postgres"]["health"],
                        services["postgres"]["persistentVolume"],
                    ],
                    [
                        "Redis",
                        services["redis"]["image"],
                        f'{services["redis"]["health"]} / auth / AOF',
                        services["redis"]["persistentVolume"],
                    ],
                ],
                [24 * mm, 62 * mm, 43 * mm, 41 * mm],
                font_size=7.0,
            ),
            p("실행 안전 설정", "h2"),
            bullet(f'Execution mode: {data["configuration"]["executionMode"]}'),
            bullet(f'Network mode: {data["configuration"]["networkMode"]}'),
            bullet("Telemetry disabled, no-new-privileges, restart: unless-stopped"),
            PageBreak(),
        ]
    )

    # 4. Assetization
    story.extend(
        [
            p("3. 서버 배포 과정의 자산화", "h1"),
            callout(
                "배포 경험을 사람의 기억에 남기지 않고 Compose, 스크립트, Runbook, 구조화 증적과 재생성 가능한 PDF/PPTX로 관리한다.",
                color=PALE_BLUE,
                text_color=BLUE,
            ),
            Spacer(1, 5 * mm),
            make_table(
                [
                    ["자산", "책임"],
                    ["compose.yml", "App, Worker, PostgreSQL, Redis, Network, Volume, Health 정의"],
                    [".env.example", "값이 없는 설정 계약. 실제 .env는 서버에서 0600으로 생성"],
                    ["install-docker-ubuntu.sh", "Docker 공식 Ubuntu 저장소 기반 설치"],
                    ["init-env.sh", "서버 로컬 비밀값 생성. 값 미출력"],
                    ["deploy.sh", "구성 검증, Pull, 순차 기동, 통합 Health"],
                    ["healthcheck.sh / status.sh", "서비스 Health, HTTP, Worker Polling과 자원 상태"],
                    ["verify-persistence.sh", "PostgreSQL 및 Redis 재시작 영속성 확인"],
                    ["remove.sh", "기본 볼륨 보존. 명시 확인 시에만 데이터 제거"],
                    ["Runbook", "사전 점검부터 업그레이드, 복구, 장애 분석, 제거까지"],
                ],
                [53 * mm, 117 * mm],
                font_size=7.1,
            ),
            p("관리 원칙", "h2"),
            bullet("구성 변경은 저장소 자산을 먼저 변경한 뒤 동일 파일을 서버에 배포한다."),
            bullet("배포 후 저장소 파일과 서버 파일의 SHA-256 일치성을 확인한다."),
            bullet("구조화 JSON을 PDF, PPTX와 Manifest의 단일 내용 원본으로 사용한다."),
            PageBreak(),
        ]
    )

    # 5. Deployment procedure
    story.extend(
        [
            p("4. 표준 배포 절차", "h1"),
            make_table(
                [
                    ["단계", "명령 / 자산", "성공 판정"],
                    ["1. 사전 점검", "OS, CPU, Memory, Disk, Time, Port", "Ubuntu 24.04, 자원 및 8080 미사용"],
                    ["2. 자산 설치", "deploy/compose/activepieces", "/opt/ablestack-techflow/activepieces"],
                    ["3. Docker 설치", "install-docker-ubuntu.sh", "Engine, Compose, docker active"],
                    ["4. 환경 생성", "init-env.sh", ".env 존재, mode 0600"],
                    ["5. 구성 검증", "docker compose config --quiet", "문법 및 필수 변수 통과"],
                    ["6. 배포", "deploy.sh", "네 서비스 healthy"],
                    ["7. 준비 확인", "healthcheck.sh / status.sh", "HTTP 200, Worker Polling Ready"],
                    ["8. 영속성", "verify-persistence.sh", "DB와 Redis 재시작 전후 동일"],
                    ["9. 재부팅 복구", "sudo reboot", "Docker, 4 services, HTTP, Polling 복구"],
                ],
                [25 * mm, 73 * mm, 72 * mm],
                font_size=7.2,
            ),
            p("초기 플랫폼 관리자", "h2"),
            bullet("배포 완료 뒤 운영자가 사설망 UI에 접속해 초기 관리자 계정을 생성한다."),
            bullet("관리자 이메일과 비밀번호는 저장소, Issue, 보고서 또는 서버 배포 스크립트에 넣지 않는다."),
            bullet("관리자 생성 전에도 Health와 Worker 준비 검증은 완료할 수 있다."),
            p("업그레이드와 제거", "h2"),
            bullet("업그레이드는 버전과 Digest 정책 검토, 백업, Pull, 기동, Health 순으로 수행한다."),
            bullet("remove.sh는 기본적으로 볼륨을 보존하며 데이터 삭제에는 확인 변수가 필요하다."),
            PageBreak(),
        ]
    )

    # 6. Verification
    verification_rows = [["ID", "검증", "결과"]]
    for item in data["verification"]:
        detail = item["result"].upper()
        if "httpStatus" in item:
            detail += f' / HTTP {item["httpStatus"]}'
        if "errors" in item:
            detail += f' / errors {item["errors"]} / warnings {item["warnings"]}'
        if "leaks" in item:
            detail += f' / leaks {item["leaks"]}'
        verification_rows.append([item["id"], item["name"], detail])
    story.extend(
        [
            p("5. 통합 검증 결과", "h1"),
            make_table(verification_rows, [16 * mm, 101 * mm, 53 * mm], font_size=7.3),
            Spacer(1, 5 * mm),
            callout(
                "V1-V10 전체 PASS. 컨테이너 Health만으로 완료하지 않고 HTTP, Worker Polling, 영속성, 호스트 재부팅과 비밀값 로그 노출을 함께 확인했다."
            ),
            p("Worker 준비 판정", "h2"),
            p(
                "호스트 재부팅 직후 Worker는 App의 Socket.IO 준비를 기다리며 재연결한다. healthcheck.sh는 컨테이너 healthy 상태에 더해 'Polling worker started' 로그가 나타날 때까지 기다린다."
            ),
            PageBreak(),
        ]
    )

    # 7. Persistence and reboot
    snapshot = data["resourceSnapshot"]
    story.extend(
        [
            p("6. 영속성과 재부팅 복구", "h1"),
            p("영속성 검증", "h2"),
            bullet("PostgreSQL의 공개 테이블 수를 기록하고 서비스 재시작 뒤 동일 값을 확인했다."),
            bullet("Redis에 임시 Probe를 기록하고 AOF 기반 재시작 뒤 동일 값을 확인했다."),
            bullet("검증용 Redis Probe만 제거하고 실제 영속 볼륨은 보존했다."),
            p("호스트 재부팅 복구", "h2"),
            make_table(
                [
                    ["검증", "결과"],
                    ["Boot time UTC", data["verification"][7]["bootTimeUtc"]],
                    ["Docker service", "enabled / active"],
                    ["App / Worker / PostgreSQL / Redis", "all healthy"],
                    ["Private Health API", "HTTP 200"],
                    ["Worker", "Socket.IO connected / polling ready"],
                    ["Post-ready error / warning", "0 / 0"],
                ],
                [62 * mm, 108 * mm],
            ),
            p("재부팅 후 자원 관측", "h2"),
            make_table(
                [
                    ["App", "Worker", "PostgreSQL", "Redis"],
                    [
                        snapshot["appMemory"],
                        snapshot["workerMemory"],
                        snapshot["postgresMemory"],
                        snapshot["redisMemory"],
                    ],
                ],
                [42.5 * mm] * 4,
            ),
            p(
                "자원 수치는 단일 시점 관측이며 용량 계획 기준이 아니다. 지속 관측과 경보 기준은 Issue #17에서 정의한다.",
                "small",
            ),
            PageBreak(),
        ]
    )

    # 8. Security and operations
    story.extend(
        [
            p("7. 보안 및 운영 통제", "h1"),
            make_table(
                [
                    ["통제", "적용 상태"],
                    ["HTTP 노출", "172.16.0.231:8080 사설 주소에만 바인딩"],
                    ["데이터 포트", "PostgreSQL과 Redis host port 미노출"],
                    ["비밀정보", ".env mode 0600, 저장소 미커밋, 생성 시 값 미출력"],
                    ["Redis", "인증과 AOF 사용"],
                    ["실행", "SANDBOX_CODE_ONLY, network STRICT, worker concurrency 1"],
                    ["컨테이너", "no-new-privileges, restart unless-stopped"],
                    ["로그", "준비 완료 후 오류 0, 경고 0, 비밀값 노출 0"],
                    ["데이터 제거", "명시 확인 변수 없이는 볼륨 보존"],
                ],
                [50 * mm, 120 * mm],
            ),
            p("운영 경계", "h2"),
            bullet("외부 HTTPS, Webhook 경로와 서명 검증은 Issue #14에서 구현한다."),
            bullet("정식 Secret Broker, 교체 및 폐기 정책은 Issue #15에서 구현한다."),
            bullet("백업과 복구 훈련은 Issue #16에서 구현한다."),
            bullet("로그, 메트릭, 이상 탐지와 경보는 Issue #17에서 구현한다."),
            bullet("버전, Digest, 업그레이드 및 롤백 정책은 Issue #18에서 구현한다."),
            PageBreak(),
        ]
    )

    # 9. Observations and follow-ups
    story.extend(
        [
            p("8. 관찰 사항과 후속 작업", "h1"),
            p("관찰 사항", "h2"),
            bullet("서버 재부팅 뒤 Worker가 App 준비를 기다린 후 정상 연결되어 Polling을 시작했다."),
            bullet("빈 AP_SSRF_ALLOW_LIST 값은 경고를 만들 수 있어 환경 계약과 실서버 설정에서 제거했다."),
            bullet("관측 이미지 Digest는 검증 JSON에 기록했으며 정식 Pinning 정책은 별도 이슈로 관리한다."),
            p("후속 이슈", "h2"),
            make_table(
                [
                    ["이슈", "목표"],
                    ["#14", "외부 HTTPS, Webhook 경로와 서명 검증"],
                    ["#15", "비밀정보 저장, 교체, 폐기"],
                    ["#16", "PostgreSQL과 Redis 백업 및 복구 훈련"],
                    ["#17", "로그, 메트릭, 대시보드와 경보"],
                    ["#18", "Activepieces 버전, 이미지 Digest, 업그레이드 및 롤백"],
                    ["#19", "GitHub PR Merge Webhook 첫 업무 Flow 실증"],
                ],
                [25 * mm, 145 * mm],
            ),
            callout(
                "Issue #13은 실행 기반을 완성한다. 첫 실제 업무 자동화의 기능 성공 기준은 Issue #19에서 검증한다.",
                color=PALE_AMBER,
                text_color=AMBER,
            ),
            PageBreak(),
        ]
    )

    # 10. Completion and sources
    story.extend(
        [
            p("9. 완료 판정과 근거", "h1"),
            callout(
                "최종 판정: VALIDATED. 재현 가능한 Compose 배포 자산과 서버 운영 Runbook을 확보했고 실서버에서 Health, 영속성 및 재부팅 복구를 통과했다."
            ),
            p("검토할 자산", "h2"),
            bullet("deploy/compose/activepieces/ - 실행 가능한 배포 자산"),
            bullet("docs/runbooks/activepieces-compose-deployment.md - 전체 서버 배포 및 운영 절차"),
            bullet("docs/reports/issue-13-activepieces-compose-deployment-validation.md - Markdown 검증 기록"),
            bullet("docs/decisions/activepieces-compose-deployment.json - 구조화 단일 원본"),
            bullet("output/issue-13-artifact-manifest.json - 크기와 SHA-256 증적"),
            p("외부 근거", "h2"),
            bullet("Activepieces Docker Compose: https://www.activepieces.com/docs/install/options/docker-compose"),
            bullet("Activepieces Workers: https://www.activepieces.com/docs/install/architecture/workers"),
            bullet("Docker Engine on Ubuntu: https://docs.docker.com/engine/install/ubuntu/"),
            bullet("GitHub Issue #13: https://github.com/ablecloud-team/ablestack-techflow/issues/13"),
            p("보안 확인", "h2"),
            p(
                "공개 자산에는 SSH 비밀번호, Activepieces API Key, JWT Secret, 암호화 키, PostgreSQL 및 Redis 실제 비밀번호를 포함하지 않는다. 초기 관리자 계정은 운영자가 사설 UI에서 별도로 생성한다."
            ),
        ]
    )

    doc.build(story)
    print(OUTPUT_PATH)


if __name__ == "__main__":
    build()
