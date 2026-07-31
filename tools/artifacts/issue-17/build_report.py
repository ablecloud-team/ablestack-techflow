#!/usr/bin/env python3
"""Build the Issue #17 observability validation report PDF."""

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
from reportlab.platypus import BaseDocTemplate, Frame, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[3]
DATA_PATH = ROOT / "docs" / "decisions" / "techflow-observability.json"
OUTPUT_PATH = ROOT / "output" / "pdf" / "techflow-observability-report.pdf"

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
        ParagraphStyle("bullet", parent=styles["body"], leftIndent=4 * mm, firstLineIndent=-3 * mm, spaceAfter=2 * mm),
    )


def table(rows: list[list[object]], widths: list[float], font_size: float = 7.4) -> Table:
    body_style = ParagraphStyle("table_body", parent=styles["table"], fontSize=font_size, leading=font_size * 1.42)
    converted = []
    for row_no, row in enumerate(rows):
        style = styles["table_head"] if row_no == 0 else body_style
        converted.append([Paragraph(escape(str(value)).replace("\n", "<br/>"), style) for value in row])
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
    result.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), background),
        ("BOX", (0, 0), (-1, -1), 0.7, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
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
            title="TechFlow 로그·메트릭·상태 점검 완료 보고서",
            author="ABLESTACK TechFlow",
            subject="GitHub Issue #17",
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
        canvas.drawString(18 * mm, A4[1] - 11 * mm, "ABLESTACK TechFlow · Observability · Issue #17")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, str(doc.page))
        canvas.restoreState()


def build() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    baseline = data["baseline"]
    drill = data["failureDrill"]
    security = data["security"]
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    story: list[object] = []

    story += [
        Spacer(1, 22 * mm),
        p("ABLESTACK TECHFLOW", "meta"),
        Spacer(1, 6 * mm),
        p("로그·메트릭·상태 점검\n완료 보고서", "title"),
        Spacer(1, 7 * mm),
        p("실행 상태를 1분마다 확인하고 장애의 발생·원인·복구를 추적", "subtitle"),
        Spacer(1, 20 * mm),
        callout("VALIDATED · 6/6 HEALTHY · 43 METRIC SERIES · 12 CONTROLS PASS"),
        Spacer(1, 28 * mm),
        table([
            ["항목", "값"],
            ["GitHub Issue", "#17 로그·메트릭·상태 점검 구성"],
            ["검증 시각", data["validatedAt"]],
            ["환경", "Ubuntu 24.04 · Activepieces 0.86.3"],
            ["수집 주기", "60초"],
            ["현재 경보", "Critical 0 · Warning 0"],
            ["상태", data["status"].upper()],
        ], [42 * mm, 128 * mm]),
        Spacer(1, 8 * mm),
        p("이 문서와 구조화 증적에는 비밀번호, API Key, Flow Payload, 사용자 식별자와 원문 로그가 포함되지 않는다.", "small"),
        PageBreak(),
    ]

    story += [
        p("1. 결과 요약", "h1"),
        callout("Gateway 장애를 Critical로 감지하고 원인을 식별했으며, 복구 후 동일 경보의 해제까지 확인했다."),
        Spacer(1, 5 * mm),
        table([
            ["영역", "실증", "판정"],
            ["서비스", "6개 Compose Health", "PASS"],
            ["엔드포인트", "내부 App·Gateway·외부 HTTPS 200", "PASS"],
            ["데이터 계층", "PostgreSQL·Redis 상태와 핵심 지표", "PASS"],
            ["백업", "Timer·직전 결과·최신 Archive", "PASS"],
            ["장애 감지", "Gateway Stop → Exit 2·원인 2건", "PASS"],
            ["알림", "systemd OnFailure journal", "PASS"],
            ["복구", "Gateway Start → 경보 Resolved", "PASS"],
            ["보안", "관측 자산 Secret 누출 0", "PASS"],
        ], [38 * mm, 98 * mm, 34 * mm]),
        p("운영 의미", "h2"),
        bullet("상태 확인과 경보 판정이 수동 명령 모음이 아니라 반복 가능한 1분 주기 자산이 되었다."),
        bullet("활성 경보뿐 아니라 발생·해제 전이를 기록해 장애 구간과 복구 시점을 추적한다."),
        bullet("M0 알림은 호스트 JSONL·journal이며 외부 알림 Adapter는 수신 책임 확정 후 연결한다."),
        PageBreak(),
    ]

    story += [
        p("2. 관측 구조와 데이터 최소화", "h1"),
        table([
            ["입력", "저장하는 값", "저장하지 않는 값"],
            ["Docker·HTTP", "Health·상태·응답시간·재시작 수", "원문 응답·환경 전체"],
            ["PostgreSQL", "DB 크기·연결·상태별 실행 수·지연", "Flow ID·Step·Payload"],
            ["Redis", "Client·메모리·거부·RDB/AOF 상태", "Key·Value"],
            ["Gateway 로그", "허용된 level/message/reason별 수", "요청 본문·서명·식별자"],
            ["App·Worker 로그", "오류 행 수", "원문 로그"],
            ["Backup", "Timer·결과·Archive 나이·크기", "Archive 내용"],
        ], [35 * mm, 65 * mm, 70 * mm]),
        p("출력 자산", "h2"),
        bullet("status.json: 최신 상태 스냅샷"),
        bullet("metrics.prom: Prometheus Text Format"),
        bullet("current-alerts.json: 현재 활성 경보"),
        bullet("alerts.jsonl: 경보 발생·해제 전이"),
        bullet("drills/*.json: 값 없는 장애 훈련 증적"),
        PageBreak(),
    ]

    story += [
        p("3. 실서버 기준선", "h1"),
        table([
            ["항목", "관측값"],
            ["루트 파일시스템 사용률", f'{baseline["rootDiskUsedRatio"] * 100:.2f}%'],
            ["사용 가능 메모리", f'{baseline["memoryAvailableRatio"] * 100:.2f}%'],
            ["서비스 Health", f'{baseline["healthyServices"]}/{baseline["totalServices"]}'],
            ["Endpoint", f'{baseline["internalAppStatus"]} / {baseline["internalGatewayStatus"]} / {baseline["publicAppStatus"]}'],
            ["PostgreSQL", f'{baseline["postgresConnections"]}/{baseline["postgresMaxConnections"]} connections · {baseline["postgresDatabaseBytes"]:,} Bytes'],
            ["Redis", f'{baseline["redisConnectedClients"]} clients · rejected {baseline["redisRejectedConnections"]} · persistence ok/ok'],
            ["최신 Backup", f'{baseline["backupLatestBytes"]:,} Bytes · Timer active'],
            ["Prometheus", f'{baseline["prometheusSeries"]} metric series'],
            ["활성 경보", f'Critical {baseline["activeCriticalAlerts"]} · Warning {baseline["activeWarningAlerts"]}'],
        ], [52 * mm, 118 * mm]),
        Spacer(1, 5 * mm),
        callout("현재 Flow 실행 이력이 없어 상태별 실행 수와 지연 분포는 빈 시계열이다.", background=PALE_AMBER, border=AMBER),
        Spacer(1, 4 * mm),
        p("수집 경로와 경보 임계값은 단위 테스트 7건으로 확인했다. 실제 Flow 상태·지연 데이터는 후속 사내 업무 Flow에서 생성 후 실증한다."),
        PageBreak(),
    ]

    story += [
        p("4. 장애 감지와 복구 실증", "h1"),
        table([
            ["단계", "관측", "결과"],
            ["정상 수집", "경보 0", "Exit 0"],
            ["Gateway Stop", "서비스·Endpoint 실패", "대상 한정"],
            ["Strict 수집", "Critical 2건", f'Exit {drill["observedExitCode"]}'],
            ["원인", "service_event-gateway", "OPENED"],
            ["원인", "endpoint_internal_gateway", "OPENED"],
            ["systemd", "OnFailure → techflow-alert", drill["systemdOnFailureNotification"]],
            ["Gateway Start", "6/6 Health·HTTPS 200", drill["postRecoveryHealth"]],
            ["재수집", "두 경보 해제", "RESOLVED"],
        ], [34 * mm, 92 * mm, 44 * mm]),
        p("추적 절차", "h2"),
        bullet("status 명령에서 심각도와 컴포넌트를 확인한다."),
        bullet("current-alerts에서 고정 키와 안전한 요약을 확인한다."),
        bullet("alerts.jsonl에서 발생·해제 시간대를 확인한다."),
        bullet("Runbook 진단 후 재수집해 같은 키의 해제를 확인한다."),
        PageBreak(),
    ]

    verification_rows = [["ID", "검증", "결과"]]
    for item in data["verification"]:
        result = item["result"]
        if "count" in item:
            result += f' ({item["count"]})'
        verification_rows.append([item["id"], item["name"], result])
    story += [
        p("5. 통합 검증과 보안", "h1"),
        table(verification_rows, [16 * mm, 119 * mm, 35 * mm], 6.8),
        Spacer(1, 5 * mm),
        callout("V1–V12 전체 PASS. 관측 파일 5개를 런타임 Secret 6종과 대조해 누출 0건을 확인했다."),
        p("보안 판정", "h2"),
        bullet(f'원문 로그 저장: {security["rawLogsPersistedByObserver"]}'),
        bullet(f'Flow Payload 저장: {security["flowPayloadsPersisted"]}'),
        bullet("환경 파일은 Bind·Port·Public URL·Backup 경로만 Allowlist로 읽는다."),
        bullet("관측 파일은 root:root 0640, 디렉터리는 0750으로 제한한다."),
        PageBreak(),
    ]

    story += [
        p("6. 완료 판정과 다음 단계", "h1"),
        callout("최종 판정: VALIDATED. Issue #17의 장애 감지·원인 추적·운영 문서·보안 반영 기준을 충족했다."),
        Spacer(1, 6 * mm),
        table([
            ["완료 자산", "역할"],
            ["ADR-0004", "데이터 최소화·메트릭·경보·책임 경계"],
            ["Observer·Timer", "1분 수집·Strict 판정·OnFailure 알림"],
            ["Compose logging", "6개 서비스 10m × 3"],
            ["검증 스크립트", "단위·Health·권한·Secret Scan"],
            ["장애 훈련", "Gateway 감지·원인·복구·해제"],
            ["Runbook", "설치·점검·대응·훈련·롤백"],
            ["JSON·PDF·PPTX·Manifest", "일관된 완료 증적"],
        ], [58 * mm, 112 * mm]),
        p("후속 실행 순서", "h2"),
        bullet("Issue #18: Activepieces 버전·이미지 Digest 고정과 업그레이드 정책"),
        bullet("Issue #19: GitHub PR Merge Webhook 기반 첫 사내 업무 자동화 Flow"),
        bullet("실제 Flow 데이터가 생성되면 상태별 실행 수와 p95 지연을 검증한다."),
        bullet("중앙 메트릭 저장과 외부 알림은 수신 책임과 보존 정책을 정한 뒤 확장한다."),
        Spacer(1, 8 * mm),
        p("고객 공개 여부는 제품 책임자의 별도 결정이며 구현 완료 판정을 제한하지 않는다.", "small"),
    ]

    doc = Report(str(OUTPUT_PATH))
    doc.build(story)
    print(OUTPUT_PATH)


if __name__ == "__main__":
    build()
