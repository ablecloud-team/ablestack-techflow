#!/usr/bin/env python3
"""Build the Issue #71 Flarum upgrade validation report PDF."""

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
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "docs/evidence/issue-71/flarum-1.8.18-validation.json"
OUTPUT = ROOT / "output/pdf/techflow-flarum-1.8.18-upgrade-report.pdf"
FONT, BOLD = "MalgunGothic", "MalgunGothicBold"
pdfmetrics.registerFont(TTFont(FONT, "C:/Windows/Fonts/malgun.ttf"))
pdfmetrics.registerFont(TTFont(BOLD, "C:/Windows/Fonts/malgunbd.ttf"))

INK = colors.HexColor("#101010")
GRAY = colors.HexColor("#5B616B")
LINE = colors.HexColor("#D4D8DF")
BLUE = colors.HexColor("#3D8DFF")
PALE = colors.HexColor("#EAF5FB")
GREEN = colors.HexColor("#117A4B")
AMBER = colors.HexColor("#A15C00")
base = getSampleStyleSheet()
styles = {
    "meta": ParagraphStyle("meta", parent=base["Normal"], fontName=BOLD, fontSize=8.5, leading=12, textColor=GRAY),
    "title": ParagraphStyle("title", parent=base["Title"], fontName=BOLD, fontSize=24, leading=33, textColor=INK),
    "subtitle": ParagraphStyle("subtitle", parent=base["Normal"], fontName=FONT, fontSize=11, leading=18, textColor=GRAY),
    "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName=BOLD, fontSize=16, leading=23, textColor=INK, spaceAfter=4 * mm),
    "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName=BOLD, fontSize=12, leading=18, textColor=INK, spaceBefore=2 * mm, spaceAfter=2 * mm),
    "body": ParagraphStyle("body", parent=base["BodyText"], fontName=FONT, fontSize=9, leading=14.5, textColor=colors.HexColor("#30343B"), spaceAfter=2.2 * mm),
    "small": ParagraphStyle("small", parent=base["BodyText"], fontName=FONT, fontSize=7.5, leading=11, textColor=GRAY),
    "table": ParagraphStyle("table", parent=base["BodyText"], fontName=FONT, fontSize=7.5, leading=10.5, textColor=colors.HexColor("#30343B")),
    "table_head": ParagraphStyle("table_head", parent=base["BodyText"], fontName=BOLD, fontSize=7.5, leading=10.5, textColor=colors.white),
}


def para(value: object, style: str = "body") -> Paragraph:
    return Paragraph(escape(str(value)).replace("\n", "<br/>"), styles[style])


def table(rows: list[list[object]], widths: list[float]) -> Table:
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


def callout(text: str, color=GREEN) -> Table:
    item = Table([[para(text)]], colWidths=[174 * mm])
    item.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE),
        ("BOX", (0, 0), (-1, -1), 1.25, color),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return item


def footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont(FONT, 7)
    canvas.setFillColor(GRAY)
    canvas.drawString(18 * mm, 10 * mm, "ABLESTACK TechFlow - Issue #71")
    canvas.drawRightString(192 * mm, 10 * mm, f"{doc.page:02d}")
    canvas.restoreState()


data = json.loads(SOURCE.read_text(encoding="utf-8"))
staging = data["staging"]
integrity = data["integrity"]
production = data["production_rollout"]
final = production["final"]
functional = data["functional_validation"]
residual = data["security"]["accepted_residual"]

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
doc = BaseDocTemplate(
    str(OUTPUT), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
    topMargin=16 * mm, bottomMargin=17 * mm,
    title="TechFlow Flarum 1.8.18 업데이트 및 롤백 검증 보고서",
    author="ABLESTACK TechFlow",
)
doc.addPageTemplates([PageTemplate(
    id="normal",
    frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="content")],
    onPage=footer,
)])

story = [
    Spacer(1, 19 * mm),
    para("ABLESTACK TECHFLOW · ISSUE #71", "meta"), Spacer(1, 8 * mm),
    para("Flarum 1.8.18 업데이트 및\n운영 반영 보고서", "title"), Spacer(1, 6 * mm),
    para("WSL 반복 리허설을 거쳐 운영 Community를 업데이트하고 데이터 정합성, 브라우저 기능과 TechFlow 통합을 확인한 결과입니다.", "subtitle"),
    Spacer(1, 17 * mm),
    callout("Go 완료 - 운영 Community는 Flarum 1.8.18이며 데이터와 첨부가 변경 전후 정확히 일치합니다."),
    Spacer(1, 8 * mm),
    para("운영 반영일 2026-08-14 · PR #75 병합 · PR #65 분리 유지", "meta"),
    PageBreak(),
    para("1. 판단 요약", "h1"),
    table([
        ["판정 항목", "결과", "의미"],
        ["반복 업데이트/롤백", "2회 PASS", "최종 패키지 집합으로 같은 결과 재현"],
        ["업무 데이터", "PASS", "사용자·토론·게시물·첨부 유지"],
        ["한글 UI", "0건", "내부 번역 키 노출 없음"],
        ["Community 기능", "PASS", "로그인·글·답글·검색·이미지·Best Answer"],
        ["TechFlow 회귀", "216/216 PASS", "AI 답변·Chat·대화·KB 계약 유지"],
        ["운영 반영", "완료", "두 번째 실행 성공, 첫 실행은 자동 롤백 검증"],
    ], [46 * mm, 35 * mm, 93 * mm]),
    Spacer(1, 7 * mm),
    callout("운영 최종 상태: Flarum 1.8.18 / Nicknames 1.8.3 / SMTP / Debug Off / HTTP 200", BLUE),
    PageBreak(),
    para("2. 검증된 패키지와 호환성", "h1"),
    table([
        ["구성요소", "기준선", "검증 상태", "판정"],
        ["Flarum Core", "1.8.10", "1.8.18", "업데이트"],
        ["Flarum Nicknames", "1.8.2", "1.8.3", "보안 권고 제거"],
        ["Symfony Mailer", "6.1.11", "6.1.11", "SMTP 조건부 고정"],
        ["PHP", "8.3.6", "유지", "호환"],
        ["MariaDB", "10.11.13", "유지", "호환"],
    ], [42 * mm, 31 * mm, 40 * mm, 61 * mm]),
    Spacer(1, 6 * mm),
    para("기능 검증 확장", "h2"),
    para("Flarum Core, Korean, FoF Upload, FoF Best Answer는 실제 사용자 시나리오로 확인했습니다."),
    para("부팅·로딩 검증 확장", "h2"),
    para("Flags, Tags, Approval, Suspend, Markdown, SEO, Sitemap, Anti-spam, Subscriptions, Sticky, Statistics, Mentions, Lock, Likes, Emoji, BBCode, Rich Text는 1.8.18 부팅과 Forum/Admin 로딩에서 오류가 없었습니다."),
    para("격리 검증 확장", "h2"),
    para("FoF Webhooks, OAuth, Pusher, Scout, ChatGPT는 외부 시스템 오염을 막기 위해 스테이징에서 발송을 끄고 TechFlow 계약 테스트로 확인했습니다."),
    PageBreak(),
    para("3. 반복 리허설과 정합성", "h1"),
    table([
        ["사이클", "업데이트", "검증", "롤백", "정합성"],
        ["validated-cycle-01", "PASS", "PASS", "PASS", "PASS"],
        ["validated-cycle-03", "PASS", "PASS", "PASS", "PASS"],
    ], [50 * mm, 31 * mm, 31 * mm, 31 * mm, 31 * mm]),
    Spacer(1, 6 * mm),
    table([
        ["지표", "기준선", "업데이트", "롤백"],
        ["사용자", integrity["users"], integrity["users"], integrity["users"]],
        ["토론", integrity["discussions"], integrity["discussions"], integrity["discussions"]],
        ["게시물", integrity["posts"], integrity["posts"], integrity["posts"]],
        ["첨부파일", integrity["upload_files"], integrity["upload_files"], integrity["upload_files"]],
        ["첨부 용량", f'{integrity["upload_bytes"]:,} B', "동일", "동일"],
        ["첨부 해시", integrity["upload_sha256"][:12] + "…", "동일", "동일"],
    ], [48 * mm, 42 * mm, 42 * mm, 42 * mm]),
    Spacer(1, 6 * mm),
    para("cycle-02의 전체 DB 해시 차이는 시작 시 만료된 access_tokens 3건이 정상 정리된 결과였습니다. 모든 다른 테이블은 동일했습니다. 이후 휘발성 토큰과 업무 데이터를 분리해 판정했고 cycle-03에서 재현성을 다시 확인했습니다."),
    PageBreak(),
    para("4. Community와 TechFlow 기능 시험", "h1"),
    table([
        ["시나리오", "결과", "비고"],
        ["한국어 Forum/Admin", "PASS", f'내부 키 {functional["korean_raw_translation_keys"]}건'],
        ["로그인·토론·답글·검색", "PASS", "AI-Assistant 계정"],
        ["이미지 첨부", "PASS", "화면 표시 확인"],
        ["Best Answer", "PASS", "솔루션 지정 확인"],
        ["일반 텍스트 첨부", "예상 거부", "대용량 로그/압축은 #72"],
        ["TechFlow 자동 테스트", "PASS", f'{functional["techflow_unittest_count"]}건'],
    ], [58 * mm, 35 * mm, 81 * mm]),
    Spacer(1, 6 * mm),
    para("스테이징 시험 토론 #166의 기능 검증을 마친 뒤 롤백으로 제거했습니다. 운영 반영 후 Community 첫 화면과 토론 상세, Community poller 회복, AI Gateway·Activepieces 상태와 보호 GitHub→Chat 가드를 확인했습니다."),
    PageBreak(),
    para("5. 보안 판단", "h1"),
    callout("Nicknames CVE-2026-30913은 1.8.3 업데이트로 제거했습니다.", GREEN),
    Spacer(1, 6 * mm),
    callout(f'{residual["package"]} {residual["version"]}의 {residual["cve"]}은 남아 있습니다. 영향 전송 방식은 {residual["affected_transport"]}이며 운영은 {residual["current_mail_driver"]}를 사용합니다.', AMBER),
    Spacer(1, 6 * mm),
    para("Flarum 1.8의 Illuminate 8은 Symfony MIME 5.4 계열을 요구하지만 Mailer 6.4는 MIME 6.2 이상을 요구하므로 함께 설치할 수 없었습니다."),
    para("운영 조건", "h2"),
    para("1. SMTP 유지  2. Sendmail 전환 금지  3. 호환 가능한 의존성 집합이 나오면 Issue #74에서 교체  4. 승인되지 않은 Composer 변경이 보이면 No-Go"),
    PageBreak(),
    para("6. 운영 실행 결과", "h1"),
    table([
        ["실행", "변경 ID", "결과", "판정"],
        ["1차", "issue-71-20260814T132041Z", "자동 롤백", "NAT loopback 점검 경로 보정"],
        ["2차", "issue-71-20260814T132424Z", "업데이트 성공", "운영 유지"],
    ], [22 * mm, 58 * mm, 38 * mm, 56 * mm]),
    Spacer(1, 6 * mm),
    table([
        ["운영 지표", "변경 전", "변경 후", "결과"],
        ["사용자", final["users"], final["users"], "일치"],
        ["토론", final["discussions"], final["discussions"], "일치"],
        ["게시물", final["posts"], final["posts"], "일치"],
        ["첨부파일", final["upload_files"], final["upload_files"], "일치"],
        ["첨부 용량", f'{final["upload_bytes"]:,} B', f'{final["upload_bytes"]:,} B', "일치"],
    ], [48 * mm, 42 * mm, 42 * mm, 42 * mm]),
    Spacer(1, 6 * mm),
    callout("백업: /var/backups/techflow-flarum/issue-71-20260814T132424Z · DB gzip SHA-256 PASS", GREEN),
    PageBreak(),
    para("7. 운영 Go/No-Go 기준", "h1"),
    table([
        ["Go", "No-Go / 즉시 롤백"],
        ["앱·설정·DB·업로드 동시 백업", "백업 또는 복원 시험 실패"],
        ["Core 1.8.18, Nicknames 1.8.3", "검증 집합과 다른 의존성 변경"],
        ["서비스 active, HTTP 200", "로그인·글·검색·첨부·Admin 실패"],
        ["업무 DB와 첨부 정합성 유지", "게시물/첨부 수 또는 해시 불일치"],
        ["한글 내부 키 0건", "번역 키 노출"],
        ["SMTP 설정 확인", "Sendmail 또는 설정 확인 불가"],
        ["Community·TechFlow E2E 통과", "AI 답변·Chat·KB 회귀 실패"],
    ], [87 * mm, 87 * mm]),
    Spacer(1, 7 * mm),
    callout("이번 운영 작업은 모든 Go 기준을 충족했습니다. 향후 재실행에서도 하나라도 No-Go이면 같은 점검 창에서 기준선으로 복원합니다.", BLUE),
    PageBreak(),
    para("8. 후속 작업", "h1"),
    para("1. Issue #72 대용량 로그·압축 업로드 개선"),
    para("2. Issue #73 Community UI 현대화"),
    para("3. Issue #74 백업·모니터링·잔여 보안 항목 강화"),
    Spacer(1, 8 * mm),
    callout("운영은 1.8.18로 전환됐고 WSL 검증 환경도 유지되어 #72와 #73 후속 작업에 사용할 수 있습니다."),
    Spacer(1, 8 * mm),
    para("근거 자산", "h2"),
    para("Runbook: docs/runbooks/flarum-1.8.18-upgrade-rollback.md\n검증 보고서: docs/reports/issue-71-flarum-1.8.18-validation.md\n구조화 증적: docs/evidence/issue-71/flarum-1.8.18-validation.json\n운영 증적: docs/evidence/issue-71/flarum-1.8.18-production-rollout.json", "small"),
]

doc.build(story)
print(OUTPUT)
