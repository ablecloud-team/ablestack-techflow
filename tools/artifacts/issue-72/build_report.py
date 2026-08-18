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
    para("일반 파일 1 GiB, 지원 압축 파일 10 GiB를 실제 운영 경로에서 수용하고 초과 파일은 거부하도록 전 계층을 정렬한 결과입니다.","subtitle"),
    Spacer(1,17*mm), callout("GO - 운영 적용 완료 · 실파일 1 GiB/10 GiB 경계 통과 · 전체 회귀 263/263"),
    Spacer(1,8*mm), para("운영 검증일 2026-08-16 · Flarum 1.8.18 · FoF Upload 1.8.5","meta"), PageBreak(),
    para("1. 판단 요약","h1"),
    make_table([["항목","결과","판정"],["일반 파일","1 GiB 허용 / +1 byte 거부","PASS"],["압축 파일","10 GiB 허용 / +1 byte 거부","PASS"],
                ["압축 분석","100 GiB, 100개, 20배","PASS"],["운영 회귀","263/263","PASS"],
                ["정리","첨부·Artifact·시험 자원 잔존 0","PASS"],["보호 서비스","github-chat-v1 frozen","PASS"]],[54*mm,83*mm,37*mm]),
    Spacer(1,7*mm), callout("정확한 경계 크기 파일을 직접 전송했고 성공 데이터는 검증 직후 삭제했습니다.",BLUE), PageBreak(),
    para("2. 계층별 현재값과 목표값","h1"),
    make_table([["계층","적용 전","적용 후"],["Nginx","120 MiB","11 GiB · 7,200초"],["PHP-FPM","120/120 MiB","파일 10 / 요청 11 GiB"],
                ["FoF Upload","50 MiB","전역 10 GiB"],["유형 정책","50 MiB","일반 1 / 압축 10 GiB"],
                ["Poller","50 MiB · 120초","1/10 GiB · 7,200초 · 2회"],["Gateway","50/100 MiB","원본 1/10 · 해제 100 GiB"]],[43*mm,58*mm,73*mm]),
    Spacer(1,6*mm), para("판정 경계는 1,073,741,824바이트와 10,737,418,240바이트로 고정했습니다."), PageBreak(),
    para("3. 안전한 처리 흐름","h1"),
    make_table([["단계","처리","안전 장치"],["1. Community","10 GiB 요청 수신","일반 1 / 압축 10 GiB"],["2. Poller","1 MiB 단위 디스크 임시 저장","동일 출처 · 2회 재시도"],
                ["3. Gateway",".part 스트리밍 + SHA-256","상한 초과 즉시 중단"],["4. 압축 검사","순차 해제 · 근거 선택","100 GiB · 100개 · 20배"],
                ["5. AI 질의","정규화 근거만 전달","원본 재파싱 금지"],["6. 보관","24시간 · 15분 정리","70%/85% 용량 이벤트"]],[37*mm,78*mm,59*mm]),
    Spacer(1,6*mm), para("10 GiB 압축 분석 중 Gateway 최대 상주 메모리는 약 60.3 MiB로 측정됐습니다."), PageBreak(),
    para("4. 실파일 경계 시험","h1"),
    make_table([["시험","Flarum","Gateway"],["일반 1 GiB","200 · 16초","201 · 27.751초"],["일반 1 GiB + 1","422 · 저장 0","400 · 선차단"],
                ["ZIP 10 GiB","200 · 410초","201 · 294.814초"],["ZIP 10 GiB + 1","413 · 저장 0","400 · 선차단"]],[73*mm,50*mm,51*mm]),
    Spacer(1,6*mm), callout("성공 첨부와 Artifact는 모두 삭제했고 Flarum DB와 파일시스템 잔존은 0건입니다.",BLUE), PageBreak(),
    para("5. 보안 및 회귀 시험","h1"),
    make_table([["시험","Gateway","결과"],
                ["경로 이탈 ZIP","400","거부"],["중첩 압축","400","거부"],["압축 폭탄","400","거부"],
                ["실행 파일 포함","400","거부"],["PNG MIME 위장","400","거부"]],[66*mm,54*mm,54*mm]),
    Spacer(1,6*mm), callout("PR #65 기반 런타임 오버레이 전체 회귀 263/263 통과",GREEN), PageBreak(),
    para("6. 운영 상태와 롤백","h1"),
    make_table([["항목","상태"],["Gateway","issue-72-large-uploads-1g10g · healthy"],["Poller","반복 처리 failed=0"],["Maintainer","level=ok · 디스크 5%"],
                ["Flarum 여유","955 GiB"],["TechFlow 여유","983,218,327,552 bytes"],["보호 서비스","frozen · guard passed"]],[62*mm,112*mm]),
    Spacer(1,6*mm), para("Flarum 백업: /var/backups/techflow-flarum/issue72-20260816T010617Z","small"),
    para("TechFlow 백업: /home/ablecloud/techflow-ai-gateway/backups/issue72-1g10g-predeploy-20260816T010000Z","small"),
    Spacer(1,7*mm), callout("Gateway, Poller, Maintainer만 교체 · DB 스키마 변경 없음",GREEN), PageBreak(),
    para("7. 최종 판정","h1"),
    callout("Issue #72 완료 조건을 모두 충족했습니다. 운영 상태는 GO입니다.",GREEN), Spacer(1,7*mm),
    para("운영자는 일반 파일 1 GiB, 압축 파일 10 GiB, Maintainer level=ok, github-chat-v1 guard passed를 핵심 상태로 확인합니다."),
    para("근거 자산","h2"), para("Runbook: docs/runbooks/community-large-uploads.md\n완료 보고서: docs/reports/issue-72-community-large-upload-validation.md\n구조화 증적: docs/evidence/issue-72/large-upload-production-validation.json","small")
]
doc.build(story); print(OUTPUT)
