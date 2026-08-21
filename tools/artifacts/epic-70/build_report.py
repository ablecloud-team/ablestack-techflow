#!/usr/bin/env python3
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
from reportlab.platypus import BaseDocTemplate, Frame, Image, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[3]
DATA = json.loads((ROOT / "docs/evidence/epic-70/community-modernization-e2e.json").read_text(encoding="utf-8"))
SCREEN = ROOT / "docs/evidence/epic-70/community-discussion-174.jpg"
OUTPUT = ROOT / "output/pdf/techflow-community-modernization-report.pdf"
FONT, BOLD = "MalgunGothic", "MalgunGothicBold"
pdfmetrics.registerFont(TTFont(FONT, "C:/Windows/Fonts/malgun.ttf"))
pdfmetrics.registerFont(TTFont(BOLD, "C:/Windows/Fonts/malgunbd.ttf"))

C = {"ink": colors.HexColor("#15253E"), "gray": colors.HexColor("#52647D"), "line": colors.HexColor("#D5E1F1"),
     "blue": colors.HexColor("#155EEF"), "green": colors.HexColor("#078248"), "pale": colors.HexColor("#EAF2FF")}
base = getSampleStyleSheet()
S = {
    "meta": ParagraphStyle("meta", parent=base["Normal"], fontName=BOLD, fontSize=8.5, leading=12, textColor=C["gray"]),
    "title": ParagraphStyle("title", parent=base["Title"], fontName=BOLD, fontSize=24, leading=33, textColor=C["ink"]),
    "subtitle": ParagraphStyle("subtitle", parent=base["Normal"], fontName=FONT, fontSize=11, leading=18, textColor=C["gray"]),
    "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName=BOLD, fontSize=16, leading=23, textColor=C["ink"], spaceAfter=4*mm),
    "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName=BOLD, fontSize=12, leading=18, textColor=C["ink"], spaceAfter=2*mm),
    "body": ParagraphStyle("body", parent=base["BodyText"], fontName=FONT, fontSize=9, leading=14.5, textColor=colors.HexColor("#30343B"), spaceAfter=2.5*mm),
    "small": ParagraphStyle("small", parent=base["BodyText"], fontName=FONT, fontSize=7.5, leading=11, textColor=C["gray"]),
    "cell": ParagraphStyle("cell", parent=base["BodyText"], fontName=FONT, fontSize=7.5, leading=10.5, textColor=colors.HexColor("#30343B")),
    "head": ParagraphStyle("head", parent=base["BodyText"], fontName=BOLD, fontSize=7.5, leading=10.5, textColor=colors.white),
}

def p(value: object, style: str = "body") -> Paragraph:
    return Paragraph(escape(str(value)).replace("\n", "<br/>"), S[style])

def table(rows: list[list[object]], widths: list[float]) -> Table:
    cells = [[p(value, "head" if index == 0 else "cell") for value in row] for index, row in enumerate(rows)]
    result = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
    result.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#243B64")), ("GRID", (0,0), (-1,-1), .35, C["line"]),
        ("VALIGN", (0,0), (-1,-1), "TOP"), ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F7F9FC")]),
        ("LEFTPADDING", (0,0), (-1,-1), 5), ("RIGHTPADDING", (0,0), (-1,-1), 5),
        ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    return result

def callout(value: str) -> Table:
    result = Table([[p(value)]], colWidths=[174*mm])
    result.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),C["pale"]),("BOX",(0,0),(-1,-1),1.2,C["green"]),
                                ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
                                ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8)]))
    return result

def footer(canvas, doc):
    canvas.saveState(); canvas.setFont(FONT, 7); canvas.setFillColor(C["gray"])
    canvas.drawString(18*mm, 10*mm, "ABLESTACK TechFlow - Epic #70")
    canvas.drawRightString(192*mm, 10*mm, f"{doc.page:02d}"); canvas.restoreState()

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
doc = BaseDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=16*mm, bottomMargin=17*mm,
                      title="TechFlow Epic #70 Community 플랫폼 현대화 완료 보고서", author="ABLESTACK TechFlow")
doc.addPageTemplates([PageTemplate(id="normal", frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="content")], onPage=footer)])

e2e = DATA["operationalE2E"]
story = [
    Spacer(1, 20*mm), p("ABLESTACK TECHFLOW · EPIC #70", "meta"), Spacer(1, 8*mm),
    p("Flarum Community 플랫폼\n현대화 완료 보고서", "title"), Spacer(1, 6*mm),
    p("업데이트·대용량 첨부·현대화 UI·운영 복구 체계를 하나의 사용자 지원 흐름으로 통합 검증한 결과입니다.", "subtitle"),
    Spacer(1, 16*mm), callout("GO · Issue #71~#74 완료 · 운영 Discussion #174 E2E 통과 · 보호 Webhook 변경 0건"),
    Spacer(1, 8*mm), p("2026-08-21 · Flarum 1.8.18 · Ubuntu 24.04", "meta"), PageBreak(),

    p("1. 완료 판단", "h1"),
    table([["영역","결과","판정"], ["Flarum 업데이트","1.8.18 · 롤백 재현","PASS"],
           ["대용량 첨부","일반 1 GiB · 압축 10 GiB","PASS"], ["UI 현대화","Desktop·Mobile·한글·접근성","PASS"],
           ["운영 복구","Backup·Restore·Monitor·Security","PASS"], ["통합 E2E","질문→AI→후속→해결→KB","PASS"],
           ["Repository","AI 153 · Community 22 Tests","PASS"]], [47*mm, 90*mm, 37*mm]),
    Spacer(1, 7*mm), callout("운영 사용자 경로와 복구 경로를 함께 검증해 Epic #70을 종료할 수 있습니다."), PageBreak(),

    p("2. 운영 E2E 타임라인", "h1"),
    table([["Post / Event","내용","결과"], ["#404","이미지·로그 ZIP 질문","등록"], ["#405","첫 AI 답변","자동 게시 + Chat"],
           ["#406","라이브 마이그레이션 후속 질문","같은 Case"], ["#407","맥락 기반 후속 답변","자동 게시 + Chat"],
           ["사용자 선택","#407 해결 표시","RESOLVED"], ["#408","KB 최종본","생성·Best Answer"],
           ["KB 완료","최종 Chat 알림","PASS"]], [42*mm, 94*mm, 38*mm]),
    Spacer(1, 6*mm), p(f"Case {e2e['caseId']} · contextVersion {e2e['contextVersion']} · draftVersion {e2e['draftVersion']}"),
    Spacer(1, 4*mm), callout("질문자가 해결 답변을 선택하면 TechFlow가 내용을 KB 구조로 정리하고 새 KB Post를 최종 솔루션으로 지정합니다."), PageBreak(),

    p("3. 답변 품질과 증거 정책", "h1"),
    table([["우선순위","분석 자료","사용자 출력"], ["1","ABLESTACK 문서","친절하고 쉬운 설명"],
           ["2","Cloud Diplo와 연관 제품 코드","현재 동작 기준"], ["3","Cloud Europa Preview","출시 전 개선 참고"],
           ["4","libvirt·QEMU 공식 자료","플랫폼 원인 보완"], ["5","승인된 외부 자료","필요한 경우만"]], [25*mm, 76*mm, 73*mm]),
    Spacer(1, 6*mm), p("첫 답변은 합성 로그에서 이전 VNC 세션이 정상 종료되지 않았음을 확인했고, 후속 답변은 서비스 중단을 줄이기 위한 라이브 마이그레이션과 실행 전·중·후 CLI 확인 절차를 구체화했습니다."),
    p("내부 경로·Commit·Citation은 사용자에게 노출하지 않았습니다. KB는 증상, 원인, 해결 방법, 추가 고려사항, 적용 버전으로 구성하고 적용 버전은 ABLESTACK Diplo로 표기했습니다."), PageBreak(),

    p("4. 실제 브라우저 검증", "h1"),
    Image(str(SCREEN), width=174*mm, height=98*mm), Spacer(1, 5*mm),
    table([["확인 항목","결과"], ["제목·해결 상태","표시"], ["이미지·로그 ZIP","표시"],
           ["첫 답변·후속 대화","표시"], ["KB 최종본·적용 버전","표시"], ["최종 Best Answer","Post #408"]], [80*mm, 94*mm]), PageBreak(),

    p("5. 운영 복구와 보안", "h1"),
    table([["검증","값","판정"], ["서비스","3/3 active","PASS"], ["HTTP","200/200/200","PASS"],
           ["Backup","Timer active · integrity true","PASS"], ["WSL 전체 복원","32 Table · 11,336 File · 11초","PASS"],
           ["보안","Header 5 · World-writable 0","PASS"], ["정상 Heartbeat 알림","0건","PASS"]], [51*mm, 86*mm, 37*mm]),
    Spacer(1, 7*mm), p("Chat은 신규 질문, 후속 질문, KB 완료와 장애·복구 전이에만 사용합니다. 정상 상태를 주기적으로 알리지 않습니다."),
    Spacer(1, 4*mm), callout("복구 훈련과 운영 모니터링은 최신 Community UI를 보존한 상태에서 재검증했습니다."), PageBreak(),

    p("6. 보호 서비스와 최종 판정", "h1"),
    table([["보호 항목","작업 전후"], ["Guard","passed / passed"], ["Container ID","bf5c76824dbf...804b4c"],
           ["Image ID","sha256:ae33662e...63670e"], ["Started At","2026-08-10T07:05:05.417216322Z"],
           ["Health","healthy"], ["변경","없음"]], [62*mm, 112*mm]),
    Spacer(1, 8*mm), callout("Epic #70 완료 · 운영 통합 판정 GO · GitHub→Chat Webhook 변경 없음"),
    Spacer(1, 8*mm), p("다음 검토", "h2"), p("Draft PR #65를 최신 main 기준으로 정리하고, 이번 운영 E2E가 확인한 AI 답변 품질·연속 대화·KB 통합 동작과 Repository 테스트를 함께 최종 검토합니다."),
    p("근거 자산", "h2"), p("docs/evidence/epic-70/community-modernization-e2e.json\ndocs/runbooks/community-platform-integrated-e2e.md\ndocs/reports/epic-70-community-modernization-validation.md", "small"),
]
doc.build(story)
print(OUTPUT)
