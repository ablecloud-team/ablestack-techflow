from __future__ import annotations

import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
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
DATA_PATH = ROOT / "docs" / "decisions" / "https-webhook-ingress.json"
OUTPUT_PATH = ROOT / "output" / "pdf" / "https-webhook-ingress-report.pdf"

FONT = "MalgunGothic"
FONT_BOLD = "MalgunGothicBold"
pdfmetrics.registerFont(TTFont(FONT, "C:/Windows/Fonts/malgun.ttf"))
pdfmetrics.registerFont(TTFont(FONT_BOLD, "C:/Windows/Fonts/malgunbd.ttf"))

BLACK = colors.HexColor("#111111")
GRAY_700 = colors.HexColor("#4B5563")
GRAY_500 = colors.HexColor("#6B7280")
GRAY_300 = colors.HexColor("#D1D5DB")
BLUE = colors.HexColor("#2563EB")
PALE_BLUE = colors.HexColor("#EFF6FF")
GREEN = colors.HexColor("#117A4B")
PALE_GREEN = colors.HexColor("#E8F5EE")
AMBER = colors.HexColor("#8A5A00")
PALE_AMBER = colors.HexColor("#FFF7E6")

base = getSampleStyleSheet()
styles = {
    "meta": ParagraphStyle("meta", parent=base["Normal"], fontName=FONT, fontSize=10, leading=14, textColor=GRAY_700),
    "title": ParagraphStyle("title", parent=base["Title"], fontName=FONT_BOLD, fontSize=27, leading=38, textColor=BLACK),
    "subtitle": ParagraphStyle("subtitle", parent=base["Normal"], fontName=FONT, fontSize=14, leading=21, textColor=GRAY_700),
    "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName=FONT_BOLD, fontSize=20, leading=27, textColor=BLACK, spaceAfter=6 * mm),
    "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName=FONT_BOLD, fontSize=13, leading=19, textColor=BLACK, spaceBefore=4 * mm, spaceAfter=3 * mm),
    "body": ParagraphStyle("body", parent=base["BodyText"], fontName=FONT, fontSize=9.2, leading=14.5, textColor=colors.HexColor("#2F3136"), spaceAfter=2 * mm),
    "small": ParagraphStyle("small", parent=base["BodyText"], fontName=FONT, fontSize=7.4, leading=10.5, textColor=GRAY_500),
    "callout": ParagraphStyle("callout", parent=base["BodyText"], fontName=FONT_BOLD, fontSize=11, leading=17, textColor=BLACK),
    "table": ParagraphStyle("table", parent=base["BodyText"], fontName=FONT, fontSize=7.4, leading=10.5, textColor=colors.HexColor("#30343B")),
    "table_head": ParagraphStyle("table_head", parent=base["BodyText"], fontName=FONT_BOLD, fontSize=7.4, leading=10.5, textColor=colors.white),
}


def p(text: object, style: str = "body") -> Paragraph:
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), styles[style])


def bullet(text: str) -> Paragraph:
    return Paragraph(
        f"• {escape(text)}",
        ParagraphStyle(
            "bullet",
            parent=styles["body"],
            leftIndent=4 * mm,
            firstLineIndent=-3 * mm,
            spaceAfter=2 * mm,
        ),
    )


def table(rows: list[list[object]], widths: list[float], font_size: float = 7.4) -> Table:
    body_style = ParagraphStyle("table_body", parent=styles["table"], fontSize=font_size, leading=font_size * 1.42)
    converted = []
    for row_no, row in enumerate(rows):
        style = styles["table_head"] if row_no == 0 else body_style
        converted.append([Paragraph(escape(str(v)).replace("\n", "<br/>"), style) for v in row])
    result = Table(converted, colWidths=widths, repeatRows=1)
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.35, GRAY_300),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), BLACK),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for row_no in range(2, len(rows), 2):
        commands.append(("BACKGROUND", (0, row_no), (-1, row_no), PALE_BLUE))
    result.setStyle(TableStyle(commands))
    return result


def callout(text: str, background=PALE_GREEN, border=GREEN) -> Table:
    result = Table([[p(text, "callout")]], colWidths=[170 * mm])
    result.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), background),
                ("BOX", (0, 0), (-1, -1), 0.7, border),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return result


class Report(BaseDocTemplate):
    def __init__(self, filename: str):
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=21 * mm,
            bottomMargin=18 * mm,
            title="TechFlow HTTPS·Webhook Ingress 완료 보고서",
            author="ABLESTACK TechFlow",
            subject="GitHub Issue #14",
        )
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="normal")
        self.addPageTemplates(PageTemplate(id="all", frames=frame, onPage=self.page_chrome))

    def page_chrome(self, canvas, doc):
        if doc.page == 1:
            return
        canvas.saveState()
        canvas.setStrokeColor(GRAY_300)
        canvas.line(18 * mm, A4[1] - 14 * mm, A4[0] - 18 * mm, A4[1] - 14 * mm)
        canvas.setFont(FONT, 7)
        canvas.setFillColor(GRAY_500)
        canvas.drawString(18 * mm, A4[1] - 11 * mm, "ABLESTACK TechFlow · HTTPS·Webhook Ingress · Issue #14")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, str(doc.page))
        canvas.restoreState()


def build() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc = Report(str(OUTPUT_PATH))
    story: list[object] = []

    story += [
        Spacer(1, 22 * mm),
        p("ABLESTACK TECHFLOW", "meta"),
        Spacer(1, 6 * mm),
        p("HTTPS·Webhook Ingress\n완료 보고서", "title"),
        Spacer(1, 7 * mm),
        p("외부 HTTPS 전환과 서명·중복 방지 Webhook 수신 경로", "subtitle"),
        Spacer(1, 20 * mm),
        callout("VALIDATED · HTTPS 200 · HTTP 308 · Signed Webhook 202 · Duplicate 409 · Reboot Recovery PASS"),
        Spacer(1, 28 * mm),
        table(
            [
                ["항목", "값"],
                ["GitHub Issue", "#14 외부 HTTPS·Webhook 접속 경로 구성"],
                ["검증일", data["validatedAt"]],
                ["외부 URL", data["endpoints"]["publicUrl"]],
                ["내부 URL", data["endpoints"]["privateUrl"]],
                ["상태", data["status"].upper()],
            ],
            [42 * mm, 128 * mm],
        ),
        Spacer(1, 8 * mm),
        p("이 문서에는 계정 비밀번호, API Key, HMAC Secret과 서버의 실제 .env 값이 포함되지 않는다.", "small"),
        PageBreak(),
    ]

    story += [
        p("1. 결과 요약", "h1"),
        callout("Issue #14 완료 기준인 HTTPS를 통한 서명 Webhook 수신과 보안·운영 절차 문서화를 모두 충족했다."),
        Spacer(1, 5 * mm),
        table(
            [
                ["영역", "적용", "판정"],
                ["HTTP 전환", "호스트 한정 308, 경로·쿼리 보존", "PASS"],
                ["TLS", "Cloudflare → Origin Full (strict)", "PASS"],
                ["Webhook", "HMAC-SHA256 + Timestamp + Event ID", "PASS"],
                ["중복 방지", "Redis SET NX EX, TTL 86,400초", "PASS"],
                ["서비스", "App·Worker·DB·Redis·Gateway·Ingress", "6/6 healthy"],
                ["복구", "서비스 재시작과 서버 재부팅", "PASS"],
                ["비밀정보", "서버 .env 0600, 로그 노출 0", "PASS"],
            ],
            [38 * mm, 94 * mm, 38 * mm],
        ),
        p("영향 범위", "h2"),
        bullet("Cloudflare 규칙은 techflow.ablecloud.io 호스트에만 적용했다."),
        bullet("Zone 전체 SSL 설정은 변경하지 않아 다른 서비스의 동작을 유지했다."),
        bullet("고객 공개 여부는 별도 제품 의사결정이며 구현 완료 기준과 분리했다."),
        PageBreak(),
    ]

    story += [
        p("2. 요청 경로와 책임", "h1"),
        table(
            [
                ["홉", "책임", "실패 시"],
                ["Cloudflare Edge", "HTTP 308, Edge TLS, 호스트 분기", "외부 요청 차단"],
                ["OpenResty Origin", "유효한 Origin TLS와 사설 전달", "Cloudflare 526/연결 실패"],
                ["Caddy Ingress", "Webhook과 UI 경로 분리, 보안 헤더", "502 또는 Health 실패"],
                ["Event Gateway", "서명·시각·중복 검증", "400/401/409/503"],
                ["Redis", "Event ID 원자적 선점과 TTL", "Gateway Fail Closed"],
                ["Activepieces", "검증 완료 이벤트의 Flow 실행", "실행 결과는 별도 상태로 관리"],
            ],
            [35 * mm, 82 * mm, 53 * mm],
        ),
        p("Worker 연결", "h2"),
        p("App은 공개 기준 URL을 사용하지만 Worker는 Compose 내부 URL http://app:80을 사용한다. 외부 Edge 장애가 내부 Flow 실행 연결을 끊지 않도록 런타임 경로를 분리했다."),
        p("네트워크 노출", "h2"),
        bullet("Host에는 172.16.0.231:8080만 바인딩한다."),
        bullet("공개 Origin의 80·443만 사용하며 외부 8080은 닫혀 있다."),
        bullet("PostgreSQL과 Redis는 Compose 내부 Network에만 존재한다."),
        PageBreak(),
    ]

    story += [
        p("3. Webhook 보안 계약", "h1"),
        callout('서명 입력: "<unix-timestamp>.<raw-body>" · 알고리즘: HMAC-SHA256', background=PALE_BLUE, border=BLUE),
        Spacer(1, 5 * mm),
        table(
            [
                ["항목", "설정"],
                ["Timestamp 헤더", "X-TechFlow-Timestamp"],
                ["Event ID 헤더", "X-TechFlow-Event-Id"],
                ["Signature 헤더", "X-TechFlow-Signature: sha256=<hex>"],
                ["허용 시각차", "300초"],
                ["중복 방지 TTL", "86,400초"],
                ["최대 Body", "1,048,576 bytes"],
                ["Redis 장애", "Fail Closed · 503"],
                ["로그", "Request ID·Event ID·상태만 기록"],
            ],
            [52 * mm, 118 * mm],
        ),
        p("검증 순서", "h2"),
        bullet("경로, 메서드, 필수 헤더와 Body 크기를 확인한다."),
        bullet("Timestamp 신선도를 확인한 뒤 HMAC을 상수 시간 비교한다."),
        bullet("Redis에서 Event ID를 원자적으로 선점한 신규 이벤트만 수락한다."),
        bullet("선택적 Upstream 전달 시 Secret 헤더는 제거한다."),
        PageBreak(),
    ]

    verification_rows = [["ID", "검증", "HTTP/수치", "결과"]]
    for item in data["verification"]:
        metric = ""
        if "httpStatus" in item:
            metric = str(item["httpStatus"])
        elif "passed" in item:
            metric = f'{item["passed"]}/{item["passed"] + item["failed"]}'
        elif "leaks" in item:
            metric = str(item["leaks"])
        verification_rows.append([item["id"], item["name"], metric, item["result"].upper()])
    story += [
        p("4. 통합 검증", "h1"),
        table(verification_rows, [14 * mm, 92 * mm, 29 * mm, 35 * mm], 7.0),
        Spacer(1, 5 * mm),
        callout("V1-V12 전체 PASS. 정상 수신뿐 아니라 중복·위조·오래된 요청의 거부와 재부팅 복구까지 확인했다."),
        p("브라우저 검증", "h2"),
        p("외부 HTTPS 주소에서 인증된 Activepieces 프로젝트 화면과 영문 UI가 정상 로드되는 것을 확인했다."),
        PageBreak(),
    ]

    services = data["services"]
    story += [
        p("5. 배포 자산과 서비스", "h1"),
        table(
            [["서비스", "이미지", "상태"]]
            + [[s["name"], s["image"], s["health"]] for s in services],
            [34 * mm, 103 * mm, 33 * mm],
            6.9,
        ),
        p("재현 가능한 자산", "h2"),
        table(
            [
                ["자산", "역할"],
                ["compose.yml", "6개 서비스, Network, Health와 제한 설정"],
                ["Caddyfile", "Webhook/UI 경로 분기와 보안 헤더"],
                ["gateway.py", "HMAC·Timestamp·Redis 중복 검증"],
                ["configure-ingress.sh", "공개 URL과 서버 비밀값 안전 구성"],
                ["verify-webhook.sh", "202·409·401·401·400 자동 판정"],
                ["verify-ingress.sh", "HTTP·HTTPS·Health·Webhook 통합 판정"],
                ["Runbook + JSON", "운영 절차와 구조화 검증 증적"],
            ],
            [51 * mm, 119 * mm],
            7.1,
        ),
        PageBreak(),
    ]

    story += [
        p("6. 보안·복구 판정", "h1"),
        table(
            [
                ["통제", "적용"],
                ["TLS 범위", "TechFlow 호스트 한정 Full (strict)"],
                ["HTTP 전환", "308로 메서드와 본문 의미 보존"],
                ["Gateway 실행", "비루트, 읽기 전용, no-new-privileges"],
                ["중복 상태", "Redis 원자적 선점, 장애 시 Fail Closed"],
                ["비밀값", ".env 0600, 저장소·문서·로그 미포함"],
                ["데이터 포트", "PostgreSQL·Redis Host 미노출"],
                ["로그 검사", "Secret 노출 0건"],
            ],
            [51 * mm, 119 * mm],
        ),
        p("복구 검증", "h2"),
        bullet("Ingress와 Event Gateway 재시작 뒤 외부 통합 검증을 다시 통과했다."),
        bullet("서버 재부팅 뒤 6개 서비스와 Worker Polling이 자동 복구되었다."),
        bullet("재부팅 뒤에도 HTTP 308, HTTPS 200, Webhook 202/409/401/401/400을 재확인했다."),
        callout("롤백은 호스트 전용 Cloudflare 규칙 비활성화와 배포 전 구성 복원으로 수행하며 데이터 볼륨과 Secret은 삭제하지 않는다.", background=PALE_AMBER, border=AMBER),
        PageBreak(),
    ]

    story += [
        p("7. 완료 판정과 다음 단계", "h1"),
        callout("최종 판정: VALIDATED. Issue #14를 종료하고 Secret 수명주기와 첫 GitHub Webhook Flow 실증으로 진행할 수 있다."),
        p("검토 자산", "h2"),
        bullet("docs/runbooks/https-webhook-ingress.md"),
        bullet("docs/reports/issue-14-https-webhook-validation.md"),
        bullet("docs/decisions/https-webhook-ingress.json"),
        bullet("deploy/compose/activepieces/event-gateway/"),
        bullet("output/issue-14-artifact-manifest.json"),
        p("후속 이슈", "h2"),
        table(
            [
                ["이슈", "목표"],
                ["#15", "Secret 저장·교체·폐기"],
                ["#16", "PostgreSQL·Redis 백업과 복구 훈련"],
                ["#17", "로그·메트릭·경보"],
                ["#18", "버전·Digest·회귀 정책"],
                ["#19", "GitHub PR Merge Webhook 첫 업무 Flow"],
            ],
            [25 * mm, 145 * mm],
        ),
        p("보안 확인", "h2"),
        p("공개 산출물에는 SSH 비밀번호, Activepieces 계정 비밀번호, API Key, HMAC Secret과 서버의 실제 .env 값이 포함되지 않는다."),
    ]

    doc.build(story)
    print(OUTPUT_PATH)


if __name__ == "__main__":
    build()
