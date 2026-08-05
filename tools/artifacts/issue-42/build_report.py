#!/usr/bin/env python3
"""Build the Issue #42 implementation report PDF."""

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
OUTPUT = ROOT / "output/pdf/techflow-source-registry-report.pdf"
FONT = "MalgunGothic"
BOLD = "MalgunGothicBold"
pdfmetrics.registerFont(TTFont(FONT, "C:/Windows/Fonts/malgun.ttf"))
pdfmetrics.registerFont(TTFont(BOLD, "C:/Windows/Fonts/malgunbd.ttf"))

BLACK = colors.HexColor("#101010")
GRAY = colors.HexColor("#5B616B")
LINE = colors.HexColor("#D4D8DF")
BLUE = colors.HexColor("#3D8DFF")
PALE = colors.HexColor("#DDF3FF")
GREEN = colors.HexColor("#117A4B")
PALE_GREEN = colors.HexColor("#E8F5EE")
RED = colors.HexColor("#B42318")

base = getSampleStyleSheet()
styles = {
    "meta": ParagraphStyle("meta", parent=base["Normal"], fontName=FONT, fontSize=9, leading=13, textColor=GRAY),
    "title": ParagraphStyle("title", parent=base["Title"], fontName=BOLD, fontSize=25, leading=36, textColor=BLACK),
    "subtitle": ParagraphStyle("subtitle", parent=base["Normal"], fontName=FONT, fontSize=12, leading=19, textColor=GRAY),
    "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName=BOLD, fontSize=18, leading=26, textColor=BLACK, spaceAfter=5 * mm),
    "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName=BOLD, fontSize=12, leading=18, textColor=BLACK, spaceBefore=3 * mm, spaceAfter=2 * mm),
    "body": ParagraphStyle("body", parent=base["BodyText"], fontName=FONT, fontSize=9, leading=14, textColor=colors.HexColor("#30343B"), spaceAfter=2 * mm),
    "small": ParagraphStyle("small", parent=base["BodyText"], fontName=FONT, fontSize=7.2, leading=10.5, textColor=GRAY),
    "callout": ParagraphStyle("callout", parent=base["BodyText"], fontName=BOLD, fontSize=10.5, leading=17, textColor=BLACK),
    "table": ParagraphStyle("table", parent=base["BodyText"], fontName=FONT, fontSize=7.2, leading=10.5, textColor=colors.HexColor("#30343B")),
    "table_head": ParagraphStyle("table_head", parent=base["BodyText"], fontName=BOLD, fontSize=7.2, leading=10.5, textColor=colors.white),
}


def p(value, style="body"):
    return Paragraph(escape(str(value)).replace("\n", "<br/>"), styles[style])


def bullet(value):
    style = ParagraphStyle("bullet", parent=styles["body"], leftIndent=4 * mm, firstLineIndent=-4 * mm)
    return Paragraph(f"• {escape(value)}", style)


def table(rows, widths):
    formatted = []
    for index, row in enumerate(rows):
        style = "table_head" if index == 0 else "table"
        formatted.append([p(cell, style) for cell in row])
    result = Table(formatted, colWidths=widths, repeatRows=1, hAlign="LEFT")
    result.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#243B64")),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FC")]),
    ]))
    return result


def callout(value, background=PALE_GREEN, border=GREEN):
    result = Table([[p(value, "callout")]], colWidths=[170 * mm])
    result.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), background), ("BOX", (0, 0), (-1, -1), 1, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return result


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(FONT, 7)
    canvas.setFillColor(GRAY)
    canvas.drawString(20 * mm, 12 * mm, "ABLESTACK TechFlow · Issue #42")
    canvas.drawRightString(190 * mm, 12 * mm, str(doc.page))
    canvas.restoreState()


def page(title, body):
    return [p(title, "h1"), *body, PageBreak()]


story = [
    Spacer(1, 20 * mm), p("ABLESTACK TECHFLOW · ISSUE #42", "meta"), Spacer(1, 10 * mm),
    p("Source Registry·검역·승인\n파이프라인 구현 완료", "title"), Spacer(1, 8 * mm),
    p("7개 저장소 · 9개 Source Profile · Reviewer dhslove", "subtitle"), Spacer(1, 14 * mm),
    callout("판정: 구현·시험 서버 배포·검증 완료. 실제 Source 승인과 OpenAI 호출은 0건이며 #43 구현을 시작할 수 있다.", PALE, BLUE),
    Spacer(1, 14 * mm),
    table([["기준", "결과"], ["Gateway", "0.2.0 / 18 API"], ["Database", "18 Table / 9 Profile"], ["Canary", "34 Eligible / 0 Excluded"], ["승인·활성", "0 / 0"], ["Provider Call", "0"]], [45 * mm, 125 * mm]),
    Spacer(1, 10 * mm), p("검증일 2026-08-05 · 초기 Source Reviewer dhslove", "meta"), PageBreak(),
]

story += page("1. 구현 결과", [
    p("Issue #42는 최신 Branch Head를 후보로 발견하고 고정 Commit을 안전하게 읽어 검역한 뒤, 사람 승인 없이는 색인을 시작할 수 없는 실행 경계를 구현했다."),
    table([["구성", "완료 내용"], ["Registry", "7개 저장소·9개 불변 Profile, D0·7일 삭제 SLA·Reviewer 고정"], ["Fetcher", "Bare Git, Commit Pin, Checkout·Hook·Submodule·LFS·Build 금지"], ["Quarantine", "경로·Binary·Encoding·Size·Secret·PII·Prompt Injection"], ["API", "발견·검역·파일 판정·승인·Job 완료 포함 18 Operation"], ["DB", "Blob·File·Finding 추가, 상태·권한·멱등성 포함 18 Table"], ["Flow", "Discovery, Review/Index Template 추가; published=false"]], [35 * mm, 135 * mm]),
    Spacer(1, 7 * mm), callout("PR 병합은 코드 구현 승인이다. Source Version 승인은 Reviewer가 고정 Commit을 다시 확인한 뒤 별도로 수행한다.", PALE, BLUE),
])

profiles = [
    ["Profile", "Repository", "Branch"],
    ["SHARED_DOCS", "ablestack-docs", "master"], ["CLOUD_MAIN", "ablestack-cloud", "main"],
    ["CLOUD_DIPLO", "ablestack-cloud", "ablestack-diplo"], ["CLOUD_EUROPA", "ablestack-cloud", "ablestack-europa"],
    ["WALL_MAIN", "ablestack-wall", "main"], ["COCKPIT_DIPLO", "ablestack-cockpit-plugin", "ablestack-diplo"],
    ["GENIE_MASTER", "ablestack-genie", "master"], ["KICKSTART_MASTER", "ablestack-kickstart", "master"],
    ["QEMU_EXEC_TOOLS_MAIN", "ablestack-qemu-exec-tools", "main"],
]
story += page("2. Source Registry 기준선", [
    p("Profile은 코드 Allowlist다. 요청이 Repository·Branch·분류·License Metadata 계약과 다르면 후보를 만들지 않는다."),
    table(profiles, [48 * mm, 72 * mm, 50 * mm]),
    Spacer(1, 5 * mm), p("License Metadata는 사실 기록이며 이번 사내 분석 구현의 차단 조건이 아니다. 모든 Profile의 초기 Reviewer는 dhslove다.", "small"),
])

story += page("3. 상태·승인·보상 계약", [
    table([["상태", "진입 조건", "실패·다음 전이"], ["REGISTERED", "Remote Head를 40자 Commit으로 고정", "QUARANTINED"], ["QUARANTINED", "전체 후보 파일 정책 판정 완료", "Reviewer 승인 또는 보류"], ["APPROVED", "dhslove·expectedCommit·제외 수용 확인", "INDEXING"], ["INDEXING", "승인 Version의 Job 시작", "실패 시 APPROVED 복귀"], ["ACTIVE", "Indexed 수 = Eligible 수", "새 Version 성공 또는 철회 시 WITHDRAWN"]], [34 * mm, 73 * mm, 63 * mm]),
    Spacer(1, 6 * mm),
    bullet("같은 Operation과 Idempotency-Key는 같은 결과를 반환한다."),
    bullet("Branch Head 변경은 새 Version이며 기존 승인 효력을 승계하지 않는다."),
    bullet("부분 색인은 활성화하지 않고 기존 ACTIVE를 유지한다."),
    bullet("새 Version 전체 성공 시에만 기존 ACTIVE를 WITHDRAWN으로 전환한다."),
    bullet("Blocking 제외 수용은 명시적 Boolean과 10자 이상 Decision Note를 요구한다."),
])

story += page("4. Fetch·검역 안전성", [
    table([["영역", "허용", "차단"], ["Git", "Bare fetch, ls-tree, cat-file", "Checkout, Hook, Submodule, LFS Smudge"], ["파일", "Allowlist Text, UTF-8, ≤ 1 MiB", "Binary, NUL, Minified, Generated"], ["정보", "D0, Hash·Decision·Rule", "Secret, PII, Credential URL"], ["실행", "정적 Read", "Build, Test, Shell, File Protocol"], ["Runtime", "2 GiB tmpfs", "exec, suid, device"]], [30 * mm, 65 * mm, 75 * mm]),
    Spacer(1, 7 * mm),
    callout("검역 제외 원문은 저장하지 않는다. 파일 조회 API는 Content를 반환하지 않고 Path·Hash·Decision·Rule만 제공한다."),
])

heads = [
    ["Profile", "관찰 Head", "상태"],
    ["SHARED_DOCS", "50d50ad6c8c…", "REGISTERED"], ["CLOUD_MAIN", "a873fb1ff436…", "REGISTERED"],
    ["CLOUD_DIPLO", "19550c70d8d8…", "REGISTERED"], ["CLOUD_EUROPA", "4787b6918bfa…", "REGISTERED"],
    ["WALL_MAIN", "f27b3f1b0b35…", "REGISTERED"], ["COCKPIT_DIPLO", "c8b37dd6a4c3…", "REGISTERED"],
    ["GENIE_MASTER", "3e3c5c364f5c…", "QUARANTINED"], ["KICKSTART_MASTER", "ffe24390544d…", "REGISTERED"],
    ["QEMU_EXEC_TOOLS_MAIN", "a4b9bd60bb93…", "REGISTERED"],
]
story += page("5. 실제 Repository Canary", [
    p("9개 최신 Head를 후보로 등록했으며 비용과 위험을 제한하기 위해 GENIE_MASTER만 검역했다. Head는 시점 정보이며 승인 Commit이 아니다."),
    table(heads, [57 * mm, 65 * mm, 48 * mm]),
    Spacer(1, 5 * mm), callout("GENIE: Candidate 34 · Eligible 34 · Excluded 0 · Blocking 0 · 승인 0", PALE, BLUE),
])

story += page("6. 시험 서버 배포·검증", [
    table([["항목", "증적"], ["배포", "/home/ablecloud/techflow-ai-gateway · Compose techflow-ai-gateway"], ["Gateway", "0.2.0 · Healthy · Image b0c3fd…dd4b"], ["DB", "18 Table · 9 Profile · vector · pg_trgm"], ["Runtime", "10001:10001 · Read-only · cap_drop ALL"], ["Canary", "8 REGISTERED · 1 QUARANTINED · 0 APPROVED/ACTIVE"], ["Fail closed", "미승인 Ingestion HTTP 409 · Query ABSTAINED"], ["기존 시스템", "Activepieces 6개 Container 모두 Healthy"]], [38 * mm, 132 * mm]),
    Spacer(1, 7 * mm),
    p("배포 전 Code·Compose·Image ID와 DB Custom Dump를 /home/ablecloud/techflow-ai-gateway-backups/issue42-20260805T1105KST에 보관했다. 실제 Secret과 Source 원문은 자산에서 제외했다."),
    callout("회귀 Test 70/70 · Validator Test 4/4 · Provider Call 0", PALE_GREEN, GREEN),
])

story += page("7. 검토 항목과 다음 단계", [
    p("초기 Source Reviewer dhslove가 검토할 항목은 다음 네 가지다."),
    bullet("9개 Profile의 Repository·Branch·Reviewer가 의도와 일치하는가"),
    bullet("GENIE_MASTER 34개 파일의 Eligible·Excluded 판정이 적절한가"),
    bullet("expectedCommit·Exclusion 수용·Decision Note 승인 계약이 충분한가"),
    bullet("#43 최초 Parser·Chunk·Embedding 적용 Profile과 Commit은 무엇인가"),
    Spacer(1, 8 * mm),
    callout("다음 실행 단위: Issue #43 Parser·Chunk·OpenAI Embeddings·FTS/Identifier/Vector·RRF·Lineage·삭제 전파", PALE, BLUE),
    Spacer(1, 7 * mm),
    p("#43은 최초 Source 승인 전에 Dry-run, 부분 실패, 원자 활성화, 삭제 전파 회귀 Test를 먼저 통과해야 한다. #42의 두 Activepieces Template은 #45에서 인증된 승인 UI와 함께 게시한다."),
])

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
doc = BaseDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=20 * mm, leftMargin=20 * mm, topMargin=18 * mm, bottomMargin=20 * mm, title="TechFlow Issue #42 Source Registry 구현 완료", author="ABLESTACK TechFlow")
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
doc.addPageTemplates(PageTemplate(id="all", frames=frame, onPage=footer))
doc.build(story)
print(OUTPUT)
