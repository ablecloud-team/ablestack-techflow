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
ACTIONS = ROOT / "docs/evidence/issue-73/screenshots/after/post-actions-desktop.png"
TAG_MODAL = ROOT / "docs/evidence/issue-73/screenshots/after/tag-selection-modal-desktop.png"
PROFILE = ROOT / "docs/evidence/issue-73/screenshots/after/profile-desktop.png"
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
    Spacer(1, 8 * mm), para("검증일 2026-08-19 · Flarum 1.8.18 · Ubuntu 24.04 WSL", "meta"), PageBreak(),

    para("1. 판단 요약", "h1"),
    make_table([
        ["항목", "결과", "판정"],
        ["전용 테마", "ablecloud/community-theme", "PASS"],
        ["반응형", "1440x900 / 390x844", "PASS"],
        ["한글", "원문 core.* 키·태그창 직접 영문 0건", "PASS"],
        ["기능", "홈·목록·태그·검색·로그인·작성·해결 답변", "PASS"],
        ["롤백", "비활성화 후 HTTP 200", "PASS"],
        ["무결성", "39 / 117 / 305, 해시 동일", "PASS"],
    ], [52 * mm, 86 * mm, 36 * mm]),
    Spacer(1, 7 * mm), callout("Flarum Core, Vendor 원본, DB Schema와 운영 Community를 수정하지 않았습니다.", BLUE, PALE), PageBreak(),

    para("2. 운영 기준선", "h1"),
    screenshot(BEFORE, 174 * mm, 105.5 * mm), Spacer(1, 5 * mm),
    para("목록 간격이 좁고 해결 상태가 아이콘에 의존했습니다. 모바일에서는 탐색과 본문이 경쟁했고 AI 진행 답변과 최종 Knowledge Base의 시각적 차이가 약했습니다."), PageBreak(),

    para("3. 현대화 결과", "h1"),
    screenshot(AFTER, 174 * mm, 105.5 * mm), Spacer(1, 5 * mm),
    para("Hero는 361px에서 약 128px로 줄이고 타이틀은 로고보다 작은 28px로 조정했습니다. 왼쪽 탐색은 240px로 넓혔습니다. 토론 행은 제목·카테고리·댓글 수를 한 줄에 배치해 약 110px에서 62px로 줄였습니다. 제품 기능과 데이터 경로는 그대로입니다."), PageBreak(),

    para("4. 모바일과 답변 상태", "h1"),
    make_table([
        ["상태", "색", "의미"],
        ["일반 질문", "White", "사용자 질문과 첨부"],
        ["AI 기술지원", "Blue", "진행 중인 전문 엔지니어 답변"],
        ["추가 확인 필요", "Yellow", "로그·화면·환경 자료 요청"],
        ["최종 해결 가이드", "Green", "선택된 Knowledge Base"],
    ], [48 * mm, 34 * mm, 92 * mm]),
    Spacer(1, 5 * mm),
    Table([[screenshot(MOBILE, 58 * mm, 127 * mm), para("390px에서는 제목 2줄과 마지막 응답 정보를 유지합니다. Hero 패딩은 데스크톱 19px, 모바일 17px로 대칭이며 아바타와 제목의 중심 차이는 0px입니다.\n\n답장·좋아요·해결 선택·더 보기는 모두 아이콘과 한글 텍스트를 함께 표시합니다. 본문 길이에 관계없이 카드-버튼 간격은 설계 8px·실측 7px·편차 0px이며 모바일 가로 넘침은 0px입니다.\n\n데스크톱의 작동하지 않는 모바일 탐색 버튼은 제거하고, 모바일에서는 40x46px 버튼과 270px 서랍 동작을 유지했습니다. Footer는 Home·Blog·Docs를 원형 아이콘으로 표시합니다.")]], colWidths=[64 * mm, 110 * mm], style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")])),
    Spacer(1, 4 * mm), screenshot(ACTIONS, 112 * mm, 70 * mm), PageBreak(),

    para("5. 공통 대화상자와 한글", "h1"),
    screenshot(TAG_MODAL, 174 * mm, 98 * mm), Spacer(1, 5 * mm),
    para("작성·태그·검색·로그인과 확장 기능 대화상자는 같은 헤더, 입력 경계, 원형 닫기, 주요 확인 버튼과 2px의 부드러운 블루 포커스 링을 사용합니다. 태그 선택창의 Choose, OK, Bypass tag requirements는 주 태그를 선택하세요, 확인, 태그 필수 조건 무시로 표시합니다."),
    Spacer(1, 5 * mm), callout("공통 Modal 규칙 적용 · 태그 선택창 직접 노출 영문 0건", BLUE, PALE), PageBreak(),

    para("6. 프로필 화면 통일", "h1"),
    screenshot(PROFILE, 174 * mm, 105.5 * mm), Spacer(1, 5 * mm),
    para("프로필 Hero는 165px 블루 Gradient와 96px 아바타로 정리했습니다. 데스크톱 메뉴는 240px, 콘텐츠는 780px이며 빈 화면도 독립 카드로 표시합니다. 모바일은 한 열로 전환합니다. Likes, My media, Security, best answers는 좋아요, 내 미디어, 보안, 해결 답변으로 한글화했고 Locale warm-up에서 실제 번역값을 검증합니다."), PageBreak(),

    para("7. WSL 전체 주기", "h1"),
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
        ["콘텐츠 SHA-256", "61215257...22cb"],
        ["첨부 SHA-256", "19cdf526...97c"],
        ["한글 원문 키 / 태그·프로필 직접 영문", "0건 / 0건"],
    ], [70 * mm, 104 * mm]),
    Spacer(1, 6 * mm), callout("최종 Run ID: issue73-20260819-profile-navigation-final-v3", GREEN, PALE_GREEN), PageBreak(),

    para("8. 롤백과 운영 결정", "h1"),
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
