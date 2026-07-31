from __future__ import annotations

import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
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
DATA_PATH = ROOT / "docs" / "decisions" / "techflow-secret-management.json"
OUTPUT_PATH = ROOT / "output" / "pdf" / "techflow-secret-management-report.pdf"

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
            title="TechFlow 비밀정보 관리 완료 보고서",
            author="ABLESTACK TechFlow",
            subject="GitHub Issue #15",
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
        canvas.drawString(18 * mm, A4[1] - 11 * mm, "ABLESTACK TechFlow · Secret Lifecycle · Issue #15")
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
        p("비밀정보 관리\n완료 보고서", "title"),
        Spacer(1, 7 * mm),
        p("Secret 저장·주입·교체·폐기와 사고 대응 운영 기준", "subtitle"),
        Spacer(1, 20 * mm),
        callout("VALIDATED · 15 CONTROLS PASS · SECRET LEAKS 0 · REBOOT RECOVERY PASS"),
        Spacer(1, 28 * mm),
        table(
            [
                ["항목", "값"],
                ["GitHub Issue", "#15 비밀정보 관리 방식 결정"],
                ["검증일", data["validatedAt"]],
                ["보호 저장소", data["decision"]["pocStore"]],
                ["소유권·권한", "root:ablecloud 0640 · 상위 디렉터리 0750"],
                ["상태", data["status"].upper()],
            ],
            [42 * mm, 128 * mm],
        ),
        Spacer(1, 8 * mm),
        p("이 문서에는 계정 비밀번호, API Key, HMAC Secret과 서버의 실제 Secret 값이 포함되지 않는다.", "small"),
        PageBreak(),
    ]

    story += [
        p("1. 결과 요약", "h1"),
        callout("Issue #15 완료 기준인 비노출 저장, 런타임 주입, 접근 권한, 교체·폐기, 감사와 사고 대응을 모두 충족했다."),
        Spacer(1, 5 * mm),
        table(
            [
                ["영역", "적용", "판정"],
                ["저장", "/etc 보호 파일과 배포 Symlink", "PASS"],
                ["접근", "root:ablecloud 0640 · 디렉터리 0750", "PASS"],
                ["Webhook 교체", "Current + Previous Grace Period", "PASS"],
                ["폐기", "현재 202 · 폐기된 직전 값 401", "PASS"],
                ["영향 제한", "Event Gateway만 재생성 · Redis 유지", "PASS"],
                ["감사", "값 없는 JSONL 변경 Event", "PASS"],
                ["노출 검사", "배포 자산·컨테이너 로그", "0건"],
                ["복구", "서비스 재시작·호스트 재부팅", "PASS"],
            ],
            [38 * mm, 94 * mm, 38 * mm],
        ),
        p("제품 경계", "h2"),
        bullet("단일 서버 파일 저장소는 사내 실증 기준이다."),
        bullet("고객 제품은 TechFlow Secret Provider 뒤에 Vault, KMS 또는 배포 플랫폼 Secret 저장소를 연결한다."),
        bullet("고객 공개 여부는 제품 책임자의 별도 결정이며 구현 완료 기준과 분리한다."),
        PageBreak(),
    ]

    class_rows = [["분류", "대표 값", "교체 원칙"]]
    for item in data["classes"]:
        class_rows.append([item["id"], " · ".join(item["examples"]), item["rotation"]])
    story += [
        p("2. Secret 분류와 책임", "h1"),
        table(class_rows, [18 * mm, 67 * mm, 85 * mm], 7.0),
        p("책임 경계", "h2"),
        table(
            [
                ["주체", "책임"],
                ["제품 책임자", "Secret 유형, 보존·교체 정책과 고객 제공 방식 승인"],
                ["TechFlow 운영자", "생성·주입·교체·폐기, 접근 통제와 사고 대응"],
                ["TechFlow Core", "향후 Secret 참조 ID, 정책, 승인과 감사"],
                ["Activepieces", "Connection 암호화와 Flow 실행 · 제품 Secret 원장 아님"],
                ["Event Gateway", "현재·직전 Webhook Secret 검증과 Grace Period"],
                ["외부 제공자", "API Token과 자격증명의 최종 발급·폐기 권위"],
            ],
            [45 * mm, 125 * mm],
            7.1,
        ),
        PageBreak(),
    ]

    story += [
        p("3. 저장·주입·감사 구조", "h1"),
        table(
            [
                ["요소", "기준"],
                ["보호 디렉터리", "/etc/ablestack-techflow/secrets · root:ablecloud 0750"],
                ["보호 파일", "activepieces.env · root:ablecloud 0640"],
                ["런타임 연결", "배포 .env Symlink → 보호 파일 → Compose env_file"],
                ["변경 도구", "secretctl.sh + secret_env.py 원자적 갱신"],
                ["감사", "/var/log/ablestack-techflow/secret-audit.jsonl · 실제 값 없음"],
                ["노출 검사", "실제 값 완전 일치 검사 · 변수 이름과 건수만 출력"],
                ["일반 백업", ".env·보호 저장소·감사 로그 제외"],
            ],
            [48 * mm, 122 * mm],
        ),
        p("주입 원칙", "h2"),
        bullet("Secret은 명령행 인자로 전달하지 않고 HMAC 도구는 표준입력을 사용한다."),
        bullet("Flow JSON, GitHub Issue, 보고서와 일반 로그에는 값 또는 파생 서명을 기록하지 않는다."),
        bullet("자동 검사는 실제 값을 메모리에서 읽지만 출력에는 변수 이름과 노출 건수만 남긴다."),
        p("감사 Event", "h2"),
        p("store.bootstrap, rotate.prepare, rotate.revoke_previous, rotate.lifecycle_test가 기록되었다. 필드는 time, actor, action, target, result로 제한한다."),
        PageBreak(),
    ]

    story += [
        p("4. Webhook Secret 수명주기", "h1"),
        callout("Current → Current + Previous → 발신자 전환 → Previous 폐기", background=PALE_BLUE, border=BLUE),
        Spacer(1, 5 * mm),
        table(
            [
                ["단계", "동작", "성공 기준"],
                ["준비", "신규 Current 생성 · 기존 Current를 Previous로 이동", "Previous가 이미 있으면 거부"],
                ["Grace", "Current와 Previous 동시 검증", "각 요청 202"],
                ["전환", "발신 시스템을 신규 Current로 변경", "정상 수신 확인"],
                ["폐기", "Previous 제거 후 Gateway만 재생성", "Current 202 · Retired 401"],
                ["롤백", "유출이 없고 전환 실패 시 기존 값 복구", "정상 수신 재검증"],
                ["사고", "유출 값은 Grace 없이 즉시 폐기", "세션·Token·연결 무효화"],
            ],
            [28 * mm, 92 * mm, 50 * mm],
        ),
        p("영향 제한", "h2"),
        bullet("교체는 Event Gateway 컨테이너만 재생성한다."),
        bullet("Redis 컨테이너 ID가 교체 전후 동일함을 검증했다."),
        bullet("세 번째 Secret은 허용하지 않아 장기 Grace 상태를 방지한다."),
        PageBreak(),
    ]

    verification_rows = [["ID", "검증", "수치", "결과"]]
    for item in data["verification"]:
        metric = ""
        if "httpStatus" in item:
            metric = str(item["httpStatus"])
        elif "passed" in item:
            metric = f'{item["passed"]}/{item["passed"] + item["failed"]}'
        elif "leaks" in item:
            metric = str(item["leaks"])
        elif "requiredPresent" in item:
            metric = str(item["requiredPresent"])
        elif "bootTimeObserved" in item:
            metric = item["bootTimeObserved"]
        verification_rows.append([item["id"], item["name"], metric, item["result"].upper()])
    story += [
        p("5. 통합 검증", "h1"),
        table(verification_rows, [14 * mm, 91 * mm, 35 * mm, 30 * mm], 6.8),
        Spacer(1, 5 * mm),
        callout("V1-V15 전체 PASS. 정상 교체뿐 아니라 폐기, 영향 제한, 실제 값 노출 0건과 재부팅 복구까지 확인했다."),
        PageBreak(),
    ]

    story += [
        p("6. 백업·사고 대응", "h1"),
        callout("일반 백업과 Secret 복구본은 분리한다.", background=PALE_AMBER, border=AMBER),
        Spacer(1, 5 * mm),
        table(
            [
                ["항목", "판정"],
                ["Issue #15 신규 일반 백업", ".env 제외 PASS"],
                ["Issue #14 기존 Archive", "root 전용 0700 디렉터리, 0600 파일로 격리"],
                ["외부 암호화 Secret 복구본", "Issue #16에서 저장 위치·보존·복원 훈련 확정"],
                ["일반 데이터 복구", "PostgreSQL·Redis 격리 복구 훈련은 Issue #16"],
            ],
            [58 * mm, 112 * mm],
        ),
        p("사고 대응 순서", "h2"),
        bullet("영향 Secret과 서비스를 분류하고 신규 값 발급 또는 강제 교체를 시작한다."),
        bullet("유출 값은 Grace Period 없이 즉시 폐기하고 세션·Token·Connection을 무효화한다."),
        bullet("실제 값 비노출 방식으로 저장소, Flow, 실행 기록과 로그를 검사한다."),
        bullet("Health, Webhook 판정과 권위 시스템 상태를 다시 검증한다."),
        bullet("실제 값 없이 사고 시각, 영향, 조치와 후속 Issue를 기록한다."),
        PageBreak(),
    ]

    story += [
        p("7. 완료 판정과 다음 단계", "h1"),
        callout("최종 판정: VALIDATED. Issue #15를 종료하고 Issue #16 백업·복구 훈련으로 진행한다."),
        Spacer(1, 6 * mm),
        table(
            [
                ["완료 기준", "결과"],
                ["Git·Issue·로그 비노출 기준", "PASS"],
                ["보호 저장소·런타임 주입", "PASS"],
                ["현재·직전 Grace Period와 폐기", "PASS"],
                ["변경 감사와 사고 대응", "PASS"],
                ["저장소·로그 실제 값 노출", "0건"],
                ["서비스 재시작·호스트 재부팅", "PASS"],
                ["ADR·Runbook·JSON·PDF·PPTX·Manifest", "자산화 완료"],
            ],
            [104 * mm, 66 * mm],
        ),
        p("후속 실행 순서", "h2"),
        bullet("Issue #16: PostgreSQL·Redis 백업과 격리 복구 훈련"),
        bullet("Issue #17·#18: 로그·메트릭·경보와 버전·회귀 정책"),
        bullet("Issue #19: GitHub PR Merge Webhook 기반 첫 업무 자동화 Flow"),
        bullet("제품 확장: TechFlow Secret Provider와 Vault·KMS 연계"),
        Spacer(1, 8 * mm),
        p("작성 기준: ADR-0002, Secret 수명주기 Runbook, 구조화 검증 JSON과 실제 서버 검증 결과.", "small"),
    ]

    doc.build(story)
    print(OUTPUT_PATH)


if __name__ == "__main__":
    build()
