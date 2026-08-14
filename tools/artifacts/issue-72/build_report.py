#!/usr/bin/env python3
"""Build the Issue #72 production validation report PDF."""

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
SOURCE = ROOT / "docs/evidence/issue-72/large-upload-production-validation.json"
OUTPUT = ROOT / "output/pdf/techflow-issue-72-large-upload-report.pdf"
FONT, BOLD = "MalgunGothic", "MalgunGothicBold"
pdfmetrics.registerFont(TTFont(FONT, "C:/Windows/Fonts/malgun.ttf"))
pdfmetrics.registerFont(TTFont(BOLD, "C:/Windows/Fonts/malgunbd.ttf"))

INK, GRAY = colors.HexColor("#101010"), colors.HexColor("#5B616B")
LINE, BLUE, PALE, GREEN = colors.HexColor("#D4D8DF"), colors.HexColor("#3D8DFF"), colors.HexColor("#EAF5FB"), colors.HexColor("#117A4B")
base = getSampleStyleSheet()
styles = {
    "meta": ParagraphStyle("meta", parent=base["Normal"], fontName=BOLD, fontSize=8.5, leading=12, textColor=GRAY),
    "title": ParagraphStyle("title", parent=base["Title"], fontName=BOLD, fontSize=24, leading=33, textColor=INK),
    "subtitle": ParagraphStyle("subtitle", parent=base["Normal"], fontName=FONT, fontSize=11, leading=18, textColor=GRAY),
    "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName=BOLD, fontSize=16, leading=23, textColor=INK, spaceAfter=4*mm),
    "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName=BOLD, fontSize=12, leading=18, textColor=INK, spaceBefore=2*mm, spaceAfter=2*mm),
    "body": ParagraphStyle("body", parent=base["BodyText"], fontName=FONT, fontSize=9, leading=14.5, textColor=colors.HexColor("#30343B"), spaceAfter=2.2*mm),
    "small": ParagraphStyle("small", parent=base["BodyText"], fontName=FONT, fontSize=7.5, leading=11, textColor=GRAY),
    "table": ParagraphStyle("table", parent=base["BodyText"], fontName=FONT, fontSize=7.5, leading=10.5, textColor=colors.HexColor("#30343B")),
    "table_head": ParagraphStyle("table_head", parent=base["BodyText"], fontName=BOLD, fontSize=7.5, leading=10.5, textColor=colors.white),
}


def para(value: object, style: str = "body") -> Paragraph:
    return Paragraph(escape(str(value)).replace("\n", "<br/>"), styles[style])


def make_table(rows: list[list[object]], widths: list[float]) -> Table:
    cells = [[para(cell, "table_head" if row_index == 0 else "table") for cell in row] for row_index, row in enumerate(rows)]
    item = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
    item.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#243B64")), ("GRID", (0,0), (-1,-1), .35, LINE),
        ("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 5),
        ("RIGHTPADDING", (0,0), (-1,-1), 5), ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5), ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F7F9FC")]),
    ]))
    return item


def callout(text: str, color=GREEN) -> Table:
    item = Table([[para(text)]], colWidths=[174*mm])
    item.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),PALE),("BOX",(0,0),(-1,-1),1.25,color),
                              ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
                              ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8)]))
    return item


def footer(canvas, doc) -> None:
    canvas.saveState(); canvas.setFont(FONT, 7); canvas.setFillColor(GRAY)
    canvas.drawString(18*mm, 10*mm, "ABLESTACK TechFlow - Issue #72")
    canvas.drawRightString(192*mm, 10*mm, f"{doc.page:02d}"); canvas.restoreState()


data = json.loads(SOURCE.read_text(encoding="utf-8")); tests=data["tests"]; policy=data["policy"]
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
doc=BaseDocTemplate(str(OUTPUT),pagesize=A4,rightMargin=18*mm,leftMargin=18*mm,topMargin=16*mm,bottomMargin=17*mm,
                    title="TechFlow Issue #72 Community 대용량 첨부 개선 완료 보고서",author="ABLESTACK TechFlow")
doc.addPageTemplates([PageTemplate(id="normal",frames=[Frame(doc.leftMargin,doc.bottomMargin,doc.width,doc.height,id="content")],onPage=footer)])

story=[
    Spacer(1,19*mm), para("ABLESTACK TECHFLOW · ISSUE #72","meta"), Spacer(1,8*mm),
    para("Community 대용량 로그·압축파일\n업로드 개선 완료 보고서","title"), Spacer(1,6*mm),
    para("Flarum 수신부터 TechFlow AI 분석까지 50 MiB 경계를 일치시키고 압축 안전검사, 자동 정리, 운영 E2E를 완료한 결과입니다.","subtitle"),
    Spacer(1,17*mm), callout("GO - 운영 적용 완료, 전체 회귀 259/259, 실제 대화에서 네 종류 첨부 수집과 AI 답변 게시 확인"),
    Spacer(1,8*mm), para("운영 반영일 2026-08-15 · Flarum 1.8.18 · FoF Upload 1.8.5","meta"), PageBreak(),
    para("1. 판단 요약","h1"),
    make_table([["항목","결과","판정"],["파일 경계","50 MiB 허용 / +1 byte 거부","PASS"],["압축 분석","100 MiB, 100개, 20배","PASS"],
                ["실제 대화","로그·ZIP·GZIP·TAR.GZ + AI 답변","PASS"],["보안 거부","경로·중첩·폭탄·실행·MIME","PASS"],
                ["운영 회귀","259/259","PASS"],["보호 서비스","github-chat-v1 frozen","PASS"]],[54*mm,83*mm,37*mm]),
    Spacer(1,7*mm), callout("시험 Discussion과 업로드 33개는 영구 삭제했으며 DB 잔존 행은 0건입니다.",BLUE), PageBreak(),
    para("2. 계층별 현재값과 목표값","h1"),
    make_table([["계층","적용 전","적용 후"],["FoF Upload","10 MiB","50 MiB"],["PHP-FPM","120 MiB, 30/60초, 128 MiB","64 MiB, 300/300초, 256 MiB"],
                ["Poller","10 MiB, 30초, 재시도 없음","50 MiB, 120초, 2회"],["Gateway","10/20 MiB","50/100 MiB"],
                ["유지관리","수동","15분, 24시간, 70%/85%"]],[46*mm,61*mm,67*mm]),
    Spacer(1,6*mm), para("Nginx의 120 MiB 요청 상한은 유지해 50 MiB 파일과 멀티파트 부가정보를 충분히 감쌉니다."), PageBreak(),
    para("3. 안전한 처리 흐름","h1"),
    make_table([["단계","처리","실패 시"],["1. Community","허용 MIME, 50 MiB","사용자에게 크기/형식 안내"],["2. Poller","동일 출처, bounded read, 2회 재시도","파일별 경고 후 다른 첨부 계속"],
                ["3. Gateway","원본 50 MiB","400 안전 거부"],["4. 압축 검사","100 MiB, 100개, 20배","경로/링크/실행/중첩 차단"],
                ["5. 보관","24시간, 15분 정리","70%/85% 용량 이벤트"]],[37*mm,86*mm,51*mm]),
    Spacer(1,6*mm), para("Flarum이 압축 파일을 범용 다운로드 MIME으로 전달해도 ZIP, GZIP, TAR.GZ 파일명만 허용 MIME으로 정규화합니다."), PageBreak(),
    para("4. 경계 및 보안 시험","h1"),
    make_table([["시험","Flarum/Gateway","결과"],["50 MiB","200 / 201","허용"],["50 MiB + 1 byte","422 / 400","거부"],
                ["경로 이탈 ZIP","- / 400","거부"],["중첩 압축","- / 400","거부"],["압축 폭탄","- / 400","거부"],
                ["실행 파일 포함","- / 400","거부"],["PNG MIME 위장","- / 400","거부"]],[58*mm,58*mm,58*mm]),
    Spacer(1,6*mm), callout("Gateway 50 MiB 일반 로그 정규화 18.5초 - 운영 제한 120초 안에서 완료",BLUE), PageBreak(),
    para("5. 실제 Community E2E","h1"),
    make_table([["검증","결과"],["임시 Discussion","#172"],["첨부","일반 로그, ZIP, GZIP, TAR.GZ"],["Gateway Artifact","4개 증가"],
                ["AI 답변","자동 게시"],["시험 글","#170~#172 영구 삭제"],["시험 업로드","33개 영구 삭제"],["DB 잔존","0건"]],[66*mm,108*mm]),
    Spacer(1,7*mm), para("질문 생성부터 Poller 전달, Artifact 생성, OpenAI 답변, Community 게시까지 약 1분의 운영 흐름을 끝까지 확인했습니다."), PageBreak(),
    para("6. 운영 상태와 롤백","h1"),
    make_table([["항목","상태"],["Gateway","issue-72-large-uploads / healthy"],["Poller","running"],["Maintainer","running / restart 0"],
                ["최초 만료 정리","28개"],["TechFlow 디스크","5% 사용, level=ok"],["Flarum 여유","955 GiB"],["TechFlow 여유","917 GiB"]],[63*mm,111*mm]),
    Spacer(1,6*mm), para("Flarum 백업: /var/backups/techflow-flarum/issue72-20260814T174252Z","small"),
    para("TechFlow 백업: /home/ablecloud/techflow-ai-gateway/backups/issue72-predeploy-20260814T174430Z","small"),
    Spacer(1,7*mm), callout("WSL 적용-검증-원복-재적용 통과 · DB 스키마 변경 없음",GREEN), PageBreak(),
    para("7. 최종 판정","h1"),
    callout("Issue #72 완료 조건을 모두 충족했습니다. 운영 상태는 GO입니다.",GREEN), Spacer(1,7*mm),
    para("운영자는 50 MiB 파일 허용, 50 MiB 초과 거부, Maintainer level=ok, github-chat-v1 guard passed를 핵심 상태로 확인합니다."),
    para("근거 자산","h2"), para("Runbook: docs/runbooks/community-large-uploads.md\n완료 보고서: docs/reports/issue-72-community-large-upload-validation.md\n구조화 증적: docs/evidence/issue-72/large-upload-production-validation.json","small")
]
doc.build(story); print(OUTPUT)

