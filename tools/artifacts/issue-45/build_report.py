#!/usr/bin/env python3
"""Build the Issue #45 implementation and validation report PDF."""

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
OUTPUT = ROOT / "output/pdf/techflow-activepieces-rag-orchestration-report.pdf"
FONT, BOLD = "MalgunGothic", "MalgunGothicBold"
pdfmetrics.registerFont(TTFont(FONT, "C:/Windows/Fonts/malgun.ttf"))
pdfmetrics.registerFont(TTFont(BOLD, "C:/Windows/Fonts/malgunbd.ttf"))
BLACK, GRAY = colors.HexColor("#101010"), colors.HexColor("#5B616B")
LINE, BLUE, PALE, GREEN = colors.HexColor("#D4D8DF"), colors.HexColor("#3D8DFF"), colors.HexColor("#DDF3FF"), colors.HexColor("#117A4B")
base = getSampleStyleSheet()
styles = {
    "meta": ParagraphStyle("meta", parent=base["Normal"], fontName=FONT, fontSize=8.5, leading=12, textColor=GRAY),
    "title": ParagraphStyle("title", parent=base["Title"], fontName=BOLD, fontSize=24, leading=34, textColor=BLACK),
    "subtitle": ParagraphStyle("subtitle", parent=base["Normal"], fontName=FONT, fontSize=11, leading=18, textColor=GRAY),
    "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName=BOLD, fontSize=17, leading=25, textColor=BLACK, spaceAfter=4 * mm),
    "body": ParagraphStyle("body", parent=base["BodyText"], fontName=FONT, fontSize=9, leading=14, textColor=colors.HexColor("#30343B"), spaceAfter=2 * mm),
    "small": ParagraphStyle("small", parent=base["BodyText"], fontName=FONT, fontSize=7.3, leading=10.5, textColor=GRAY),
    "callout": ParagraphStyle("callout", parent=base["BodyText"], fontName=BOLD, fontSize=10.5, leading=17, textColor=BLACK),
    "table": ParagraphStyle("table", parent=base["BodyText"], fontName=FONT, fontSize=7.3, leading=10.5, textColor=colors.HexColor("#30343B")),
    "table_head": ParagraphStyle("table_head", parent=base["BodyText"], fontName=BOLD, fontSize=7.3, leading=10.5, textColor=colors.white),
}


def p(value, style="body"):
    return Paragraph(escape(str(value)).replace("\n", "<br/>"), styles[style])


def bullet(value):
    style = ParagraphStyle("bullet", parent=styles["body"], leftIndent=5 * mm, firstLineIndent=-4 * mm)
    return Paragraph(f"- {escape(value)}", style)


def grid(rows, widths):
    cells = [[p(cell, "table_head" if index == 0 else "table") for cell in row] for index, row in enumerate(rows)]
    table = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#243B64")), ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FC")]),
    ]))
    return table


def callout(text, color=BLUE):
    table = Table([[p(text, "callout")]], colWidths=[174 * mm])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PALE), ("BOX", (0, 0), (-1, -1), 1.2, color),
                               ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                               ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    return table


def footer(canvas, doc):
    canvas.saveState(); canvas.setFont(FONT, 7); canvas.setFillColor(GRAY)
    canvas.drawString(18 * mm, 10 * mm, "ABLESTACK TechFlow · Issue #45")
    canvas.drawRightString(192 * mm, 10 * mm, f"{doc.page:02d}"); canvas.restoreState()


OUTPUT.parent.mkdir(parents=True, exist_ok=True)
doc = BaseDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=16 * mm, bottomMargin=17 * mm,
                      title="TechFlow Issue #45 Activepieces RAG Orchestration 완료 보고서", author="ABLESTACK TechFlow")
doc.addPageTemplates([PageTemplate(id="normal", frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="content")], onPage=footer)])

story = [Spacer(1, 17 * mm), p("ABLESTACK TECHFLOW · ISSUE #45", "meta"), Spacer(1, 9 * mm),
         p("Activepieces RAG Orchestration\n구현 및 시험 서버 실증 완료", "title"), Spacer(1, 6 * mm),
         p("9개 Source Profile의 감지·승인·재색인·철회·평가를 정책 경계를 지킨 시각적 Flow로 연결했습니다.", "subtitle"),
         Spacer(1, 18 * mm), callout("97 + 26 Tests · 5 Flows Enabled · 6 Containers Healthy · Secret Leak 0"),
         Spacer(1, 8 * mm), p("AI Gateway 0.5.0 · Event Gateway 0.3.0 · 2026-08-10", "meta"), PageBreak()]

story += [p("1. 완료 판정", "h1"), grid([
    ["검증", "결과", "판정"], ["Flow", "5개 Enabled", "PASS"], ["Gateway", "AI 0.5.0 · Event 0.3.0", "PASS"],
    ["테스트", "AI 97 · Event/Flow 26", "PASS"], ["Idempotency", "첫 요청 202 · 중복 409", "PASS"],
    ["보안", "Runtime Secret Leak 0", "PASS"], ["복구", "양 Gateway 이전·현재 버전 왕복", "PASS"],
], [38 * mm, 101 * mm, 35 * mm]), Spacer(1, 6 * mm),
          callout("Activepieces는 Orchestration만 담당하고 정책과 데이터 변경은 TechFlow AI Gateway가 소유합니다.", GREEN), PageBreak()]

story += [p("2. 구조와 책임 경계", "h1"), grid([
    ["구성", "책임"], ["Event Gateway", "서명·Timestamp·Event ID·9 Profile 매핑·Payload 최소화"],
    ["Activepieces", "5개 시각적 Flow·순서·재시도·Run 이력"], ["AI Gateway", "승인·상태·Compatibility·검역·색인·삭제·평가"],
    ["PostgreSQL", "19개 RAG Table·Job/Evaluation Correlation"], ["Local Mirror", "7개 Repository Bare Mirror·고정 Commit 읽기"],
], [45 * mm, 129 * mm]), Spacer(1, 5 * mm),
          bullet("HTTP 202는 접수 성공이며 Flow Run과 Gateway 상태가 모두 확인돼야 성공입니다."),
          bullet("Source 원문과 Credential은 Flow 입력·출력·Run 이력에 남기지 않습니다."),
          bullet("Reviewer는 dhslove로 고정하고 잘못된 상태는 MANUAL_REVIEW로 종료합니다."), PageBreak()]

story += [p("3. 활성 Flow", "h1"), grid([
    ["Flow", "Runtime ID", "역할"], ["Discovery", "mmXBGOVE0cwz2JmkzKoZl", "후보 등록·검역"],
    ["Review", "FinN9dvxtiGl10t8Br8kt", "승인·고정 Commit 색인"], ["Compatibility", "zGckwpMDh3ImsHs0yig4L", "승인 조합 반영"],
    ["Withdrawal", "rpsiIRfh8wo6XpdvaxSMa", "검색 제외·Lineage 삭제"], ["Evaluation", "JV7tPXmC2cR75HGm4Oft4", "Golden Set 실행·상태"],
], [38 * mm, 56 * mm, 80 * mm]), Spacer(1, 5 * mm),
          callout("Discovery와 Evaluation Canary는 SUCCEEDED, 오류 승인 Canary는 INVALID_STATE·MANUAL_REVIEW로 Fail-closed 됐습니다."), PageBreak()]

story += [p("4. 보안·오류·멱등성", "h1"), grid([
    ["통제", "구현"], ["최소 Payload", "Source ID·Profile·Branch·Commit·Job·상태·허용 오류만"],
    ["금지", "원문·Prompt·Provider Key·GitHub Token·Authorization Header"], ["SSRF", "STRICT · 내부 172.30.19.3/32와 172.30.19.9/32만"],
    ["RETRYABLE", "Timeout·5xx · 동일 Idempotency Key로 제한 재시도"], ["TERMINAL", "계약·권한 오류 · 자동 재시도 금지"],
    ["MANUAL_REVIEW", "상태 충돌·승인 무효 · Reviewer 확인 후 새 Event"],
], [43 * mm, 131 * mm]), Spacer(1, 5 * mm),
          bullet("DROP-ME Marker를 포함한 Canary 후 Activepieces DB Dump에서 Marker가 검출되지 않았습니다."),
          bullet("Flow 배포 도구를 반복 실행해도 논리 이름 기준으로 중복 Flow를 만들지 않습니다."), PageBreak()]

story += [p("5. 시험 서버와 복구", "h1"), grid([
    ["항목", "결과"], ["Activepieces", "0.86.3 · 6개 Container Healthy"], ["AI Gateway", "0.5.0 · Database/Vector ready · OpenAI"],
    ["Root Disk", "1,005 GiB · 사용 15 GiB · 가용 949 GiB · 2%"], ["Backup", "AP Dump 86,097,054 B · AI Dump 1,013,497 B"],
    ["AI Rollback", "0.5.0 → 0.4.0 → 0.5.0"], ["Event Rollback", "0.3.0 → 0.2.0 → 0.3.0"],
], [44 * mm, 130 * mm]), Spacer(1, 5 * mm),
          p("백업 경로", "small"), p("/home/ablecloud/techflow-ai-gateway-backups/issue45-20260810T042137Z", "small"),
          Spacer(1, 5 * mm), bullet("Migration 0006의 Nullable Correlation Column은 애플리케이션 롤백 중 유지합니다."),
          bullet("DB 손상 시에만 서비스 정지 후 배포 전 Dump를 복원합니다."), PageBreak()]

story += [p("6. 운영 Gate와 다음 단계", "h1"),
          p("시크릿 브라우저 세션에서 ABLECLOUD Organization과 ABLESTACK-TechFlow Project를 확인했습니다. Project Data Retention은 None, Organization API call logging은 Enabled per call입니다. 판정은 VERIFIED_PROJECT_DATA_RETENTION_NONE입니다."),
          grid([["구분", "조치"], ["D0", "현재 PoC 운영 허용 · store=false 유지"], ["D1 이상", "별도 ZDR·MAM 승인·적용 또는 보안정책 변경 후 확대"],
                ["API Key", "사용자 요청에 따라 교체 보류"], ["Issue #45", "Draft PR 검토·병합 후 종료"], ["Issue #46", "품질·보안·E2E 검증 착수"]], [44 * mm, 130 * mm]),
          Spacer(1, 7 * mm), callout("현재 상태: IMPLEMENTED · DEPLOYED · E2E VALIDATED · ROLLBACK VERIFIED", GREEN),
          Spacer(1, 7 * mm), p("참고: https://developers.openai.com/api/docs/guides/your-data", "small")]

doc.build(story)
print(OUTPUT)
