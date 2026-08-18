#!/usr/bin/env python3
"""Build the Issue #73 Community UI modernization report PDF."""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Frame, Image, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "output/pdf/techflow-community-ui-modernization-report.pdf"
BEFORE = ROOT / "docs/evidence/issue-73/screenshots/before/home-desktop.png"
AFTER = ROOT / "docs/evidence/issue-73/screenshots/after/home-desktop.png"
MOBILE = ROOT / "docs/evidence/issue-73/screenshots/after/home-mobile.png"
FONT, BOLD = "MalgunGothic", "MalgunGothicBold"
pdfmetrics.registerFont(TTFont(FONT, "C:/Windows/Fonts/malgun.ttf"))
pdfmetrics.registerFont(TTFont(BOLD, "C:/Windows/Fonts/malgunbd.ttf"))

INK = colors.HexColor("#15253E")
GRAY = colors.HexColor("#52647D")
LINE = colors.HexColor("#D8E0EC")
BLUE = colors.HexColor("#155EEF")
PALE = colors.HexColor("#EAF2FF")
GREEN = colors.HexColor("#078248")
PALE_GREEN = colors.HexColor("#EAFAF2")
YELLOW = colors.HexColor("#FFF6DF")
base = getSampleStyleSheet()
styles = {
    "meta": ParagraphStyle("meta", parent=base["Normal"], fontName=BOLD, fontSize=8.5, leading=12, textColor=GRAY),
    "title": ParagraphStyle("title", parent=base["Title"], fontName=BOLD, fontSize=24, leading=33, textColor=INK),
    "subtitle": ParagraphStyle("subtitle", parent=base["Normal"], fontName=FONT, fontSize=11, leading=18, textColor=GRAY),
    "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName=BOLD, fontSize=16, leading=23, textColor=INK, spaceAfter=4 * mm),
    "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName=BOLD, fontSize=12, leading=18, textColor=INK, spaceBefore=2 * mm, spaceAfter=2 * mm),
    "body": ParagraphStyle("body", parent=base["BodyText"], fontName=FONT, fontSize=9, leading=14.5, textColor=colors.HexColor("#26364D"), spaceAfter=2.2 * mm),
    "small": ParagraphStyle("small", parent=base["BodyText"], fontName=FONT, fontSize=7.5, leading=11, textColor=GRAY),
    "table": ParagraphStyle("table", parent=base["BodyText"], fontName=FONT, fontSize=7.5, leading=10.5, textColor=colors.HexColor("#26364D")),
    "table_head": ParagraphStyle("table_head", parent=base["BodyText"], fontName=BOLD, fontSize=7.5, leading=10.5, textColor=colors.white),
}


def para(value: object, style: str = "body") -> Paragraph:
    return Paragraph(escape(str(value)).replace("\n", "<br/>"), styles[style])


def make_table(rows: list[list[object]], widths: list[float]) -> Table:
    cells = [[para(cell, "table_head" if row_index == 0 else "table") for cell in row] for row_index, row in enumerate(rows)]
    item = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
    item.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#243B64")),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FC")]),
    ]))
    return item


def callout(text: str, border=GREEN, fill=PALE_GREEN) -> Table:
    item = Table([[para(text)]], colWidths=[174 * mm])
    item.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), fill),
        ("BOX", (0, 0), (-1, -1), 1.25, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return item


def screenshot(path: Path, width: float, height: float) -> Image:
    image = Image(str(path), width=width, height=height)
    image.hAlign = "CENTER"
    return image


def footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont(FONT, 7)
    canvas.setFillColor(GRAY)
    canvas.drawString(18 * mm, 10 * mm, "ABLESTACK TechFlow - Issue #73")
    canvas.drawRightString(192 * mm, 10 * mm, f"{doc.page:02d}")
    canvas.restoreState()


OUTPUT.parent.mkdir(parents=True, exist_ok=True)
doc = BaseDocTemplate(
    str(OUTPUT), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
    topMargin=16 * mm, bottomMargin=17 * mm,
    title="TechFlow Issue #73 Community 인터페이스 현대화 완료 보고서",
    author="ABLESTACK TechFlow",
)
doc.addPageTemplates([PageTemplate(id="normal", frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="content")], onPage=footer)])

story = [
    Spacer(1, 19 * mm), para("ABLESTACK TECHFLOW · ISSUE #73", "meta"), Spacer(1, 8 * mm),
    para("Community 인터페이스\n현대화 완료 보고서", "title"), Spacer(1, 6 * mm),
    para("ABLESTACK 브랜드 테마 · 한글 UX · 반응형 · 비활성화 롤백", "subtitle"),
    Spacer(1, 17 * mm), callout("CONDITIONAL GO - WSL 구현·검증 완료, 운영 Community는 변경하지 않음", BLUE, PALE),
    Spacer(1, 8 * mm), para("검증일 2026-08-18 · Flarum 1.8.18 · Ubuntu 24.04 WSL", "meta"), PageBreak(),

    para("1. 판단 요약", "h1"),
    make_table([
        ["항목", "결과", "판정"],
        ["전용 테마", "ablecloud/community-theme", "PASS"],
        ["반응형", "1440x900 / 390x844", "PASS"],
        ["한글", "원문 core.* 키 0건", "PASS"],
        ["기능", "홈·목록·태그·검색·로그인", "PASS"],
        ["롤백", "비활성화 후 HTTP 200", "PASS"],
        ["무결성", "39 / 117 / 305, 해시 동일", "PASS"],
    ], [52 * mm, 86 * mm, 36 * mm]),
    Spacer(1, 7 * mm), callout("Flarum Core, Vendor 원본, DB Schema와 운영 Community를 수정하지 않았습니다.", BLUE, PALE), PageBreak(),

    para("2. 운영 기준선", "h1"),
    screenshot(BEFORE, 174 * mm, 105.5 * mm), Spacer(1, 5 * mm),
    para("목록 간격이 좁고 해결 상태가 아이콘에 의존했습니다. 모바일에서는 탐색과 본문이 경쟁했고 AI 진행 답변과 최종 Knowledge Base의 시각적 차이가 약했습니다."), PageBreak(),

    para("3. 현대화 결과", "h1"),
    screenshot(AFTER, 174 * mm, 105.5 * mm), Spacer(1, 5 * mm),
    para("Hero는 361px에서 약 128px로 줄이고 타이틀은 로고보다 작은 28px로 조정했습니다. 왼쪽 탐색은 240px로 넓혔으며 태그 페이지의 토의 시작 버튼은 도구 모음 안에 유지됩니다. 제품 기능과 데이터 경로는 그대로입니다."), PageBreak(),

    para("4. 모바일과 답변 상태", "h1"),
    make_table([
        ["상태", "색", "의미"],
        ["일반 질문", "White", "사용자 질문과 첨부"],
        ["AI 기술지원", "Blue", "진행 중인 전문 엔지니어 답변"],
        ["추가 확인 필요", "Yellow", "로그·화면·환경 자료 요청"],
        ["최종 해결 가이드", "Green", "선택된 Knowledge Base"],
    ], [48 * mm, 34 * mm, 92 * mm]),
    Spacer(1, 5 * mm),
    Table([[screenshot(MOBILE, 72 * mm, 158 * mm), para("390px에서 제목을 두 줄로 유지하고 태그는 넘침 없이 절삭합니다.\n\n입력 글자 16px, 주요 조작 44px, 3px 포커스 링, 모션 축소를 적용했습니다.\n\n사용자 화면에는 내부 근거 ID와 검토 경로를 노출하지 않습니다.")]], colWidths=[78 * mm, 96 * mm], style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")])), PageBreak(),

    para("5. WSL 전체 주기", "h1"),
    make_table([
        ["단계", "Theme", "HTTP", "콘텐츠/첨부"],
        ["기준선", "Disabled", "200", "기준 해시"],
        ["활성화", "Enabled", "200", "동일"],
        ["비활성화 롤백", "Disabled", "200", "동일"],
        ["최종 스테이징", "Enabled", "200", "동일"],
    ], [48 * mm, 42 * mm, 32 * mm, 52 * mm]),
    Spacer(1, 6 * mm),
    make_table([
        ["검증", "결과"],
        ["정적 계약", "8/8"],
        ["사용자 / 토의 / 게시물", "39 / 117 / 305"],
        ["콘텐츠 SHA-256", "83b236aa...48a8"],
        ["첨부 SHA-256", "19cdf526...97c"],
        ["한글 원문 키", "0건"],
    ], [70 * mm, 104 * mm]),
    Spacer(1, 6 * mm), callout("최종 Run ID: issue73-20260818-compact-hero-nav", GREEN, PALE_GREEN), PageBreak(),

    para("6. 롤백과 운영 결정", "h1"),
    make_table([
        ["구분", "변경 여부"],
        ["Flarum Core / Vendor", "변경 없음"],
        ["DB Schema / 콘텐츠", "변경 없음"],
        ["TechFlow Gateway / Poller", "변경 없음"],
        ["GitHub→Chat", "변경 없음"],
        ["운영 Community", "적용 전, 승인 대기"],
    ], [72 * mm, 102 * mm]),
    Spacer(1, 6 * mm),
    callout("장애 시 php flarum extension:disable ablecloud-community-theme로 기본 Flarum UI에 복귀합니다.", BLUE, PALE),
    Spacer(1, 8 * mm), para("운영 반영 승인 후 Runbook에 따라 백업, 테마 설치, 한글 Cache 검증, 데스크톱·모바일 Smoke, 콘텐츠 해시 비교를 반복합니다."),
    Spacer(1, 8 * mm), para("근거 자산", "h2"),
    para("설계: docs/plans/issue-73-community-ui-modernization.md\nRunbook: docs/runbooks/community-theme-rollout-rollback.md\n완료 보고서: docs/reports/issue-73-community-ui-validation.md\n구조화 증적: docs/evidence/issue-73/community-theme-validation.json", "small"),
]

doc.build(story)
print(OUTPUT)
