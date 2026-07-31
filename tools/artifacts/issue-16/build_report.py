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
DATA_PATH = ROOT / "docs" / "decisions" / "techflow-state-backup-recovery.json"
OUTPUT_PATH = ROOT / "output" / "pdf" / "techflow-backup-recovery-report.pdf"

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
            title="TechFlow 상태 백업·복구 완료 보고서",
            author="ABLESTACK TechFlow",
            subject="GitHub Issue #16",
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
        canvas.drawString(18 * mm, A4[1] - 11 * mm, "ABLESTACK TechFlow · State Backup & Recovery · Issue #16")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, str(doc.page))
        canvas.restoreState()


def build() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    policy = data["policy"]
    baseline = data["baseline"]
    recovery = data["recovery"]
    escrow = data["secretEscrow"]
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc = Report(str(OUTPUT_PATH))
    story: list[object] = []

    story += [
        Spacer(1, 22 * mm),
        p("ABLESTACK TECHFLOW", "meta"),
        Spacer(1, 6 * mm),
        p("상태 백업·복구\n완료 보고서", "title"),
        Spacer(1, 7 * mm),
        p("PostgreSQL·Redis 무중단 백업과 운영 비영향 격리 복구", "subtitle"),
        Spacer(1, 20 * mm),
        callout("VALIDATED · RTO 40 SEC · 15 CONTROLS PASS · ZERO RECOVERY RESOURCES"),
        Spacer(1, 28 * mm),
        table(
            [
                ["항목", "값"],
                ["GitHub Issue", "#16 PostgreSQL·Redis 백업과 복구 검증"],
                ["검증일", data["validatedAt"]],
                ["대상", "Ubuntu 24.04 · Activepieces 0.86.3"],
                ["RPO", "24시간 + 최대 10분 지연"],
                ["RTO", f'{recovery["restoreDurationSeconds"]}초 / 목표 {policy["rtoTargetSeconds"]}초'],
                ["상태", data["status"].upper()],
            ],
            [42 * mm, 128 * mm],
        ),
        Spacer(1, 8 * mm),
        p("이 문서와 구조화 증적에는 계정 비밀번호, API Key, 암호화 Key, 데이터 원문과 Probe 값이 포함되지 않는다.", "small"),
        PageBreak(),
    ]

    story += [
        p("1. 결과 요약", "h1"),
        callout("실제 운영 데이터를 정지 없이 백업해 40초 안에 격리 복원하고 운영 서비스 무영향을 확인했다."),
        Spacer(1, 5 * mm),
        table(
            [
                ["영역", "실증", "판정"],
                ["PostgreSQL", "Custom Dump · 80 Tables · Probe", "PASS"],
                ["Redis", "RDB 무결성 · 정상 Load · Probe", "PASS"],
                ["정기 실행", "매일 02:30 UTC · 실제 Service 1회", "PASS"],
                ["무결성", "Manifest · SHA-256 · Secret 제외", "PASS"],
                ["격리", "내부 Network · 공개 Port 0", "PASS"],
                ["운영 영향", "Container ID 유지 · 6 Health", "PASS"],
                ["정리", "Container·Network·Volume 0", "PASS"],
                ["Secret", "AES-256 Escrow · 격리 복호화", "PASS"],
            ],
            [40 * mm, 96 * mm, 34 * mm],
        ),
        p("제품 경계", "h2"),
        bullet("현재 수치는 M0 단일 서버와 현재 데이터 규모의 실증 결과다."),
        bullet("로컬 Backup만으로 Host 전체 상실을 보호하지 않으며 고객 제품은 Off-host 장애 영역이 필요하다."),
        bullet("고객 공개 여부는 제품 책임자의 별도 결정이며 구현 완료 기준과 분리한다."),
        PageBreak(),
    ]

    story += [
        p("2. 기준선과 정책", "h1"),
        table(
            [
                ["항목", "검증 기준선"],
                ["PostgreSQL", f'{baseline["postgresVersion"]} · {baseline["postgresDatabaseBytes"]:,} Bytes · Public Table {baseline["postgresPublicTables"]}'],
                ["PostgreSQL Volume", baseline["postgresVolumeObserved"]],
                ["Redis", f'{baseline["redisVersion"]} · 훈련 후 Key {baseline["redisKeysAfterDrill"]}'],
                ["Redis Volume", baseline["redisVolumeObserved"]],
                ["Redis Persistence", "AOF 활성 · 마지막 RDB 상태 ok"],
                ["Backup Schedule", policy["schedule"]],
                ["Retention", f'정기 {policy["scheduledRetentionDays"]}일 · 복구 훈련 {policy["recoveryDrillRetentionDays"]}일'],
            ],
            [50 * mm, 120 * mm],
        ),
        p("Snapshot 일관성", "h2"),
        bullet("PostgreSQL Dump는 하나의 논리적으로 일관된 데이터베이스 시점이다."),
        bullet("Redis RDB는 파일 생성 시점의 일관된 Snapshot이다."),
        bullet("두 저장소를 하나의 분산 트랜잭션으로 묶지 않으므로 영속 업무 원장은 PostgreSQL에 둔다."),
        bullet("Redis 상태는 Queue·Lock·중복 방지처럼 재구성·재처리 가능해야 한다."),
        PageBreak(),
    ]

    story += [
        p("3. 백업과 복구 구조", "h1"),
        table(
            [
                ["단계", "입력", "검증·출력"],
                ["Probe", "PostgreSQL · Redis", "비밀값 아닌 동일 ID"],
                ["Backup", "운영 Container", "postgres.dump · redis.rdb"],
                ["Integrity", "Snapshot Files", "manifest.json · checksums.sha256"],
                ["Restore", "격리 Network·Volume", "임시 PostgreSQL·Redis"],
                ["Verify", "복원 State", "Table · RDB · 양쪽 Probe"],
                ["Regression", "운영 Compose", "Container ID · 6 Health · HTTPS 200"],
                ["Cleanup", "임시 자원", "Container·Network·Volume·평문 0"],
            ],
            [28 * mm, 62 * mm, 80 * mm],
        ),
        p("안전 원칙", "h2"),
        bullet("운영 Volume을 복사하거나 덮어쓰지 않는다."),
        bullet("복구 컨테이너는 Host Port를 Publish하지 않는다."),
        bullet("Checksum 불일치, 안전하지 않은 경로 또는 Secret 파일 포함은 즉시 실패한다."),
        bullet("실패 자원은 기본 정리하고 분석할 때만 명시적으로 보존한다."),
        PageBreak(),
    ]

    verification_rows = [["ID", "검증", "결과"]]
    for item in data["verification"]:
        result = item["result"]
        if "statusCode" in item:
            result += f' ({item["statusCode"]})'
        verification_rows.append([item["id"], item["name"], result])
    story += [
        p("4. 통합 검증", "h1"),
        table(verification_rows, [16 * mm, 119 * mm, 35 * mm], 6.8),
        Spacer(1, 5 * mm),
        callout("V1-V15 전체 PASS. 백업 생성부터 격리 복원, 운영 회귀와 구형 Secret Archive 폐기까지 확인했다."),
        PageBreak(),
    ]

    story += [
        p("5. RPO·RTO와 Redis 판정", "h1"),
        table(
            [
                ["지표", "기준", "실증", "판정"],
                ["RPO", "24시간 + 10분", "Timer 활성·실행 성공", "PASS"],
                ["RTO", "15분 이내", f'{recovery["restoreDurationSeconds"]}초', "PASS"],
                ["운영 중단", "없음", "Container ID 유지", "PASS"],
                ["공개 면적", "Port 0", str(recovery["publishedPorts"]), "PASS"],
                ["임시 자원", "0", "Container·Network·Volume 0", "PASS"],
            ],
            [28 * mm, 45 * mm, 65 * mm, 32 * mm],
        ),
        p("Redis Key 수 해석", "h2"),
        callout(
            f'Source 관측 {recovery["redisSourceObservedKeys"]}개 · RDB 복원 {recovery["redisRestoredKeys"]}개',
            background=PALE_AMBER,
            border=AMBER,
        ),
        Spacer(1, 4 * mm),
        p("Activepieces Queue가 실행 중이어서 RDB 생성과 Source 수 집계 사이에 Key 수가 변했다. Source 관측 수는 정보성 값이며 성공 조건이 아니다."),
        bullet("RDB 파일 자체 무결성 검사를 통과했다."),
        bullet("Redis가 RDB를 오류 없이 Load했다."),
        bullet("RDB Snapshot 내부의 복구 Probe가 PostgreSQL Probe와 일치했다."),
        PageBreak(),
    ]

    story += [
        p("6. Secret 복구와 보안 영향", "h1"),
        callout("상태 Archive와 복호화 Root를 분리해 하나의 유출이 전체 복구 자산을 노출하지 않도록 했다.", background=PALE_BLUE, border=BLUE),
        Spacer(1, 5 * mm),
        table(
            [
                ["항목", "결과"],
                ["상태 Archive", ".env·보호 저장소·감사 로그 제외"],
                ["암호화", escrow["cipher"]],
                ["Passphrase", "Bundle과 분리 · 임시 파일 0600"],
                ["복구 훈련", "격리 복호화 · 필수 Key · Fingerprint PASS"],
                ["운영 Secret", "원본 변경 없음"],
                ["구형 Archive", ".env 포함 단일 파일 안전 삭제"],
                ["외부 Vault", "미연결 · 고객 Beta·GA 필수 Gate"],
            ],
            [48 * mm, 122 * mm],
        ),
        p("제품화 조건", "h2"),
        bullet("암호화 Bundle과 Passphrase를 서로 다른 승인된 외부 장애 영역에 저장한다."),
        bullet("데이터 규모별 RTO·RPO 부하 시험과 정기 복구 훈련을 수행한다."),
        bullet("Backup 실패, 최근 성공 시각, Archive 연령·용량을 Issue #17 관측 체계에 연결한다."),
        PageBreak(),
    ]

    story += [
        p("7. 완료 판정과 다음 단계", "h1"),
        callout("최종 판정: VALIDATED. Issue #16을 종료하고 Issue #17 운영 관측 체계로 진행한다."),
        Spacer(1, 6 * mm),
        table(
            [
                ["완료 기준", "결과"],
                ["백업 주기·보존·복구 절차", "정책·코드·Systemd로 확정"],
                ["격리 복구 훈련", "PostgreSQL·Redis PASS"],
                ["복구 시간 측정", "40초 · 목표 15분 이내"],
                ["운영·보안 영향", "무중단 · Port 0 · Secret 분리"],
                ["임시 자원 정리", "Container·Network·Volume 0"],
                ["ADR·Runbook·JSON·PDF·PPTX·Manifest", "자산화 완료"],
            ],
            [104 * mm, 66 * mm],
        ),
        p("후속 실행 순서", "h2"),
        bullet("Issue #17: 로그·메트릭·상태 점검과 Backup 실패 알림"),
        bullet("Issue #18: Activepieces 버전·이미지 Digest 고정과 회귀 정책"),
        bullet("Issue #19: GitHub PR Merge Webhook 기반 첫 업무 자동화 Flow"),
        bullet("고객 Beta·GA: Off-host Backup과 외부 Vault 장애 영역 구성"),
        Spacer(1, 8 * mm),
        p("작성 기준: ADR-0003, 상태 백업·복구 Runbook, 구조화 검증 JSON과 실제 서버 검증 결과.", "small"),
    ]

    doc.build(story)
    print(OUTPUT_PATH)


if __name__ == "__main__":
    build()
