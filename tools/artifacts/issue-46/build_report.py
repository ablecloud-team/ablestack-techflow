#!/usr/bin/env python3
"""Build the Issue #46 PDF report including every Golden Question and answer."""

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
SOURCE = ROOT / "output/issue-46-live-evaluation.json"
EVIDENCE = ROOT / "output/issue-46-server-evidence.json"
OUTPUT = ROOT / "output/pdf/techflow-golden-set-quality-security-e2e-report.pdf"
FONT, BOLD = "MalgunGothic", "MalgunGothicBold"
pdfmetrics.registerFont(TTFont(FONT, "C:/Windows/Fonts/malgun.ttf"))
pdfmetrics.registerFont(TTFont(BOLD, "C:/Windows/Fonts/malgunbd.ttf"))
BLACK, GRAY, LINE = colors.HexColor("#101010"), colors.HexColor("#5B616B"), colors.HexColor("#D4D8DF")
BLUE, PALE, GREEN, RED = colors.HexColor("#3D8DFF"), colors.HexColor("#DDF3FF"), colors.HexColor("#117A4B"), colors.HexColor("#B42318")
base = getSampleStyleSheet()
styles = {
    "meta": ParagraphStyle("meta", parent=base["Normal"], fontName=FONT, fontSize=8.3, leading=12, textColor=GRAY),
    "title": ParagraphStyle("title", parent=base["Title"], fontName=BOLD, fontSize=23, leading=33, textColor=BLACK),
    "subtitle": ParagraphStyle("subtitle", parent=base["Normal"], fontName=FONT, fontSize=10.5, leading=17, textColor=GRAY),
    "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName=BOLD, fontSize=16, leading=23, textColor=BLACK, spaceAfter=4 * mm),
    "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName=BOLD, fontSize=12, leading=18, textColor=BLACK, spaceAfter=2 * mm),
    "body": ParagraphStyle("body", parent=base["BodyText"], fontName=FONT, fontSize=8.5, leading=13.5, textColor=colors.HexColor("#30343B"), spaceAfter=2 * mm),
    "small": ParagraphStyle("small", parent=base["BodyText"], fontName=FONT, fontSize=7, leading=10, textColor=GRAY),
    "table": ParagraphStyle("table", parent=base["BodyText"], fontName=FONT, fontSize=6.8, leading=9.5, textColor=colors.HexColor("#30343B")),
    "table_head": ParagraphStyle("table_head", parent=base["BodyText"], fontName=BOLD, fontSize=6.8, leading=9.5, textColor=colors.white),
}


def p(value: object, style: str = "body") -> Paragraph:
    return Paragraph(escape(str(value)).replace("\n", "<br/>"), styles[style])


def grid(rows: list[list[object]], widths: list[float]) -> Table:
    cells = [[p(cell, "table_head" if index == 0 else "table") for cell in row] for index, row in enumerate(rows)]
    table = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#243B64")),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FC")]),
    ]))
    return table


def callout(text: str, passed: bool = True) -> Table:
    table = Table([[p(text, "body")]], colWidths=[174 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE), ("BOX", (0, 0), (-1, -1), 1.2, GREEN if passed else RED),
        ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return table


def footer(canvas, doc) -> None:
    canvas.saveState(); canvas.setFont(FONT, 7); canvas.setFillColor(GRAY)
    canvas.drawString(18 * mm, 10 * mm, "ABLESTACK TechFlow · Issue #46")
    canvas.drawRightString(192 * mm, 10 * mm, f"{doc.page:02d}"); canvas.restoreState()


data = json.loads(SOURCE.read_text(encoding="utf-8"))
evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
summary, records = data["summary"], data["records"]
boundary_violations = summary.get("securityBoundaryAnsweredViolations", summary["isolationAnsweredViolations"])
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
doc = BaseDocTemplate(
    str(OUTPUT), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=16 * mm, bottomMargin=17 * mm,
    title="TechFlow Issue #46 Golden Set 품질 보안 E2E 완료 보고서", author="ABLESTACK TechFlow",
)
doc.addPageTemplates([PageTemplate(id="normal", frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="content")], onPage=footer)])

story = [
    Spacer(1, 18 * mm), p("ABLESTACK TECHFLOW · ISSUE #46", "meta"), Spacer(1, 8 * mm),
    p("Golden Set·품질·보안·E2E\n검증 완료 보고서", "title"), Spacer(1, 6 * mm),
    p(f"실제 시험 서버에서 실행한 {summary['totalCases']}개 질문의 기대 답변, 실제 답변, Citation, 자동 판정과 Codex 판정을 모두 포함한다.", "subtitle"),
    Spacer(1, 18 * mm), callout(
        f"{summary['passedCases']} / {summary['totalCases']} 자동 통과 · "
        f"{summary.get('codexAcceptedCases', 0)} / {summary['totalCases']} Codex 수용 · "
        f"답변 Citation {summary['answeredCitationRate'] * 100:.0f}% · "
        f"격리·보안 경계 위반 {boundary_violations}건",
        summary["codexAcceptableAnswerRate"] >= .8,
    ),
    Spacer(1, 8 * mm), p(f"AI Gateway 0.6.0 · Event Gateway 0.4.0 · Run {data['runId']}", "meta"), PageBreak(),
    p("1. 품질 Gate", "h1"),
    grid([
        ["Gate", "기준", "실측", "판정"],
        ["Codex 수용 가능 답변율", "≥80%", f"{summary['codexAcceptableAnswerRate'] * 100:.1f}%", "PASS" if summary['codexAcceptableAnswerRate'] >= .8 else "FAIL"],
        ["자동 엄격 답변 통과율", "관찰", f"{summary['acceptableAnswerRate'] * 100:.1f}%", "REVIEW"],
        ["올바른 보류율", "≥90%", f"{summary['correctAbstentionRate'] * 100:.1f}%", "PASS" if summary['correctAbstentionRate'] >= .9 else "FAIL"],
        ["Citation 포함률", "100%", f"{summary['answeredCitationRate'] * 100:.1f}%", "PASS" if summary['answeredCitationRate'] == 1 else "FAIL"],
        ["코드 라인 해석률", "100%", f"{summary['codeLineResolvableRate'] * 100:.1f}%", "PASS" if summary['codeLineResolvableRate'] == 1 else "FAIL"],
        ["격리·보안 경계 위반", "0", boundary_violations, "PASS" if boundary_violations == 0 else "FAIL"],
        ["Provider P95", "≤12초", f"{summary['providerP95Ms']:,}ms", "PASS" if summary['providerP95Ms'] <= 12000 else "FAIL"],
    ], [54 * mm, 35 * mm, 45 * mm, 40 * mm]), Spacer(1, 7 * mm),
    p("Reference Replay 70/70은 계약 검증용이며 위 표의 실 Gateway 품질 수치에는 사용하지 않았다."), PageBreak(),
    p("2. 배포·색인·복구", "h1"),
    p(f"배포 이미지: {evidence.get('aiGatewayImage')} / {evidence.get('eventGatewayImage')}"),
    p(f"롤백: {evidence.get('rollback')}"),
    p(f"백업: {evidence.get('aiBackup')} / {evidence.get('activepiecesBackup')}", "small"),
    Spacer(1, 5 * mm),
    grid([["Source", "상태", "Files", "Chunks", "Symbols", "Relations"]] + [
        [item['sourceProfileId'], item['state'], item.get('metrics', {}).get('indexedFiles', 0),
         item.get('metrics', {}).get('chunks', 0), item.get('metrics', {}).get('symbols', 0),
         item.get('metrics', {}).get('relations', 0)] for item in evidence.get('sources', [])
    ], [42 * mm, 26 * mm, 25 * mm, 27 * mm, 27 * mm, 27 * mm]), PageBreak(),
    p("3. 보안·장애 개선", "h1"),
    p("D0 전용, store=false, Provider Tool 0개를 유지했다. 질문·답변 원문은 평가 산출물에만 보존하고 DB와 Activepieces에는 저장하지 않는다."),
    p("긴 단일 UTF-8 라인을 임베딩 한도 아래로 분할하고, 공백 파일이 빈 임베딩 입력을 만들지 않도록 고쳤다. 1,024자를 넘는 Parser 관계명은 SHA-256 접미사로 결정적 축약하며 DB 고유키가 같은 중복 Chunk는 첫 항목만 보존한다. 기본 Mock Compose와 실 OpenAI Override를 분리하고 Active Source는 무중단 REINDEX로 교체한다. 대규모 교체의 외래키 검사 병목은 참조 측 부분 인덱스 2개로 제거했고 Embedding Batch는 최대 128개·UTF-8 합계 256KiB로 동적 분할한다. 실패 로그는 Job ID·예외 유형·안전한 오류 코드만 남긴다."),
    p(f"삭제 드릴: {evidence.get('deletionDrill')}"),
    p("ZDR은 사용하지 않으며 구현·배포·완료 Gate가 아니다."), PageBreak(),
    p("4. Golden Question별 결과", "h1"),
    p("이하 70개 문항은 사용자 검토를 위해 생략 없이 수록했다."), PageBreak(),
]

for index, record in enumerate(records, 1):
    auto, review = record["automatedJudgment"], record["reviewJudgment"]
    citation_rows = [["Profile", "Branch", "Commit", "Path / Lines"]]
    for citation in record["citations"]:
        citation_rows.append([
            citation.get("sourceProfileId"), citation.get("branch"), str(citation.get("commit", ""))[:12],
            f"{citation.get('path')}:{citation.get('startLine')}-{citation.get('endLine')}",
        ])
    story += [
        p(f"{index:02d}. {record['caseKey']} — {review['verdict']}", "h2"),
        p(f"범위: {', '.join(record['sourceProfileIds'])} · 기대 {record['expectedState']} · 실제 {record['actualState']} · {record['latencyMs']:,}ms", "meta"),
        p(f"Question\n{record['question']}"),
        p(f"기대 답변\n{record.get('expectedAnswer') or '(답변하지 않고 보류)'}"),
        p(f"실제 답변\n{record.get('actualAnswer') or '(답변 없음)'}"),
        callout(
            f"자동 {'PASS' if auto['passed'] else 'FAIL'} · concept {auto['conceptCoverage']:.2f} · "
            f"사유 {', '.join(auto['reasons']) if auto['reasons'] else '없음'}\n"
            f"Codex {review['verdict']} · {review['rationale']}",
            bool(auto["passed"]),
        ),
        Spacer(1, 4 * mm),
    ]
    if len(citation_rows) > 1:
        story.append(grid(citation_rows, [31 * mm, 31 * mm, 30 * mm, 82 * mm]))
    else:
        story.append(p(f"Citation 없음 · 보류 사유: {record.get('abstainReason') or '없음'}", "small"))
    story.append(PageBreak())

story += [p("5. 최종 판정", "h1"), callout(
    "Issue #46은 구현·시험 서버 배포·실 Golden Set 평가·보안·롤백·산출물 검증 결과를 기준으로 판정한다.",
    summary["codexAcceptableAnswerRate"] >= .8 and summary["correctAbstentionRate"] >= .9 and boundary_violations == 0,
)]
doc.build(story)
print(OUTPUT)
