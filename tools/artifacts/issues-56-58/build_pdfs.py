#!/usr/bin/env python3
"""Build and verify-layout-ready report and slide PDFs for Issues #56-#58."""

from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "output/pdf"
REPORT = OUT / "techflow-assist-multimodal-report.pdf"
SLIDES = OUT / "techflow-assist-multimodal-presentation.pdf"
EVAL = json.loads((ROOT / "output/issues-56-58-reference-evaluation.json").read_text(encoding="utf-8"))
LIVE = json.loads((ROOT / "output/issues-56-58-live-evaluation.json").read_text(encoding="utf-8"))


def register_font() -> str:
    candidates = [Path("C:/Windows/Fonts/malgun.ttf"), Path("C:/Windows/Fonts/arial.ttf")]
    for path in candidates:
        if path.exists():
            pdfmetrics.registerFont(TTFont("TechFlow", str(path)))
            return "TechFlow"
    return "Helvetica"


FONT = register_font()
BLUE = colors.HexColor("#17365D")
LIGHT = colors.HexColor("#EEF4FA")
RED = colors.HexColor("#B42318")


def styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"], fontName=FONT, fontSize=26, leading=34, textColor=BLUE, alignment=TA_LEFT, spaceAfter=12),
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName=FONT, fontSize=18, leading=24, textColor=BLUE, spaceAfter=9),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName=FONT, fontSize=13, leading=18, textColor=BLUE, spaceBefore=6, spaceAfter=5),
        "body": ParagraphStyle("body", parent=base["BodyText"], fontName=FONT, fontSize=9.5, leading=15, wordWrap="CJK", spaceAfter=5),
        "small": ParagraphStyle("small", parent=base["BodyText"], fontName=FONT, fontSize=7.5, leading=11, wordWrap="CJK"),
        "cover": ParagraphStyle("cover", parent=base["Title"], fontName=FONT, fontSize=30, leading=40, textColor=colors.white, alignment=TA_CENTER),
        "coverSub": ParagraphStyle("coverSub", parent=base["BodyText"], fontName=FONT, fontSize=13, leading=20, textColor=colors.white, alignment=TA_CENTER),
    }


S = styles()


def p(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text.replace("\n", "<br/>"), S[style])


def tbl(rows, widths, header=True):
    value = Table([[p(str(cell), "small") for cell in row] for row in rows], colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("FONTNAME", (0, 0), (-1, -1), FONT), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9AA7B4")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        commands += [("BACKGROUND", (0, 0), (-1, 0), BLUE), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white)]
    value.setStyle(TableStyle(commands))
    return value


def footer(canvas, doc):
    canvas.saveState(); canvas.setFont(FONT, 7); canvas.setFillColor(colors.HexColor("#65758B"))
    canvas.drawString(18 * mm, 10 * mm, "ABLESTACK TechFlow · Issues #56–#58")
    canvas.drawRightString(192 * mm, 10 * mm, str(doc.page)); canvas.restoreState()


def build_report():
    OUT.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(REPORT), pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=18*mm, bottomMargin=18*mm, title="TechFlow Assist 종합·멀티모달 완료 보고")
    story = []
    cover = Table([[p("ABLESTACK TechFlow", "coverSub")], [p("Assist 종합·멀티모달\n완료 보고", "cover")], [p("Issues #56–#58 · 2026-08-11", "coverSub")]], colWidths=[174*mm], rowHeights=[30*mm, 110*mm, 40*mm])
    cover.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), BLUE), ("VALIGN", (0,0), (-1,-1), "MIDDLE")]))
    story += [cover, PageBreak()]

    story += [p("1. 완료 요약", "h1"), p("단일 영역 RAG를 종합 질문·이미지 입력까지 확장했다. Planner는 대상 영역과 Cloud 브랜치를 결정하고, 복수 저장소는 승인된 Compatibility Set에서만 결합한다. 이미지와 검색 근거는 하나의 strict JSON 보고서로 합성하되 관찰·진단·조치·미확인 사항을 분리한다."),
              tbl([["항목","결과"],["AI Gateway","0.7.0 / OpenAI / Health READY"],["자동 시험","118/118 PASS"],["Golden Set","종합 15 + 멀티모달 12 = 27/27 기준 PASS"],["Activepieces","Assist Flow 2개 ENABLED / E2E Run SUCCEEDED"],["보호 서비스","github-chat-v1 동결 가드 전·후 PASS"]],[45*mm,125*mm]),
              Spacer(1,6*mm), p("결론", "h2"), p("사용자가 질문과 화면을 함께 제시하면 ABLESTACK 문서·소스코드를 종합해 기술지원 보고서를 작성하는 MVP 경로를 실증했다. 고객 공개 여부는 별도 제품 결정이다."), PageBreak()]

    story += [p("2. 아키텍처와 책임", "h1"),
              tbl([["단계","소유자","실패 시 동작"],["Webhook·실행","Activepieces","Run 실패를 관찰하고 AI 정책을 대신 판단하지 않음"],["Artifact 검증","AI Gateway","D0·형식·크기·해상도 불일치 400"],["질문 계획","Planner","브랜치·제품 범위 불명확 시 NEEDS_INFORMATION"],["호환성","Resolver","복수 저장소 승인 세트 없으면 생성 전 중단"],["검색","Hybrid Retrieval","고정 Commit 활성 Source Version만 사용"],["합성","Responses Adapter","근거 부족·충돌·판독 불가 시 ABSTAINED"]],[32*mm,55*mm,83*mm]),
              Spacer(1,6*mm), p("OpenAI 경계", "h2"), p("이미지는 Base64 data URL의 input_image와 detail=original로 전달한다. tools=[], store=false, background=false와 strict JSON Schema를 강제한다. 이미지 속 문구는 증거일 뿐 지시가 아니다."), PageBreak()]

    screen = ROOT / "services/ai-gateway/app/data/golden-artifacts/synthetic-vm-error.png"
    story += [p("3. 판독 가능한 화면 실증", "h1"), Image(str(screen), width=165*mm, height=99*mm), Spacer(1,4*mm),
              p("질문", "h2"), p("Analyze the attached ABLESTACK Europa VM deployment failure screen together with CLOUD_EUROPA source evidence."),
              p("답변 요약", "h2"), p("VM DEPLOYMENT FAILED, Host allocation, ERROR 530, Insufficient capacity를 관찰했다. 동시에 D0 SYNTHETIC TEST ARTIFACT 표기를 인식해 실제 운영 장애 원인으로 단정하지 않았다."),
              p("판정: PASS", "h2"), p("Artifact ID와 Source Citation을 함께 사용했고 합성 화면을 운영 사실로 오인하지 않았다."), PageBreak()]

    story += [p("4. 실서버 질문·답변·판정", "h1")]
    for case in LIVE["cases"]:
        story.append(KeepTogether([p(f"{case['caseId']} · {case['state']}", "h2"), p(f"<b>질문</b>  {case['question']}"), p(f"<b>답변</b>  {case['answer']}"), p(f"<b>판정</b>  {case['judgment']} — {case['reason']}"), Spacer(1,3*mm)]))
    story.append(PageBreak())

    story += [p("5. Golden Question 27건", "h1"), p("각 행은 질문, 제품이 반환해야 할 응답 경계, 판정을 포함한다. 기계 판독본은 output/issues-56-58-reference-evaluation.json이다.")]
    rows = [["ID","유형","질문","응답 기준","판정"]]
    for item in EVAL["results"]:
        rows.append([item["caseId"], item["type"], item["question"], item["response"], item["judgment"]])
    story += [tbl(rows, [18*mm,22*mm,65*mm,55*mm,14*mm]), PageBreak()]

    story += [p("6. 보안·보존 정책", "h1"),
              tbl([["정책","구현"],["분류","D0만 허용"],["형식","PNG/JPEG/WebP, 매직 바이트 일치"],["크기","10 MiB/파일, 5개/질문"],["해상도","12,000 px/변, 총 40M px"],["보존","기본 24시간, 최대 168시간"],["권한","전용 Volume, 디렉터리 0700, 파일 0600"],["삭제","명시 삭제 후 GET 404"],["로그","이미지 바이트·질문·모델 원문 미기록"]],[42*mm,128*mm]),
              Spacer(1,6*mm), p("시험 중 수정", "h2"), p("12초 읽기 제한은 고추론 종합 생성에 부족해 연결 3초·읽기 90초·재시도 1회로 분리했다. 모델이 정확한 Artifact ID를 복사하도록 ID·형식·SHA256 Manifest와 허용 Evidence ID를 입력에 추가했다."), PageBreak()]

    story += [p("7. 배포·복구", "h1"),
              tbl([["항목","증적"],["서버","Ubuntu 24.04 / Root 1005 GiB"],["배포","AI Gateway 0.7.0 / issue-58"],["Image ID",LIVE["gateway"]["imageId"]],["백업",LIVE["backup"]],["Activepieces Run",LIVE["activepieces"]["e2eRunId"]+" / SUCCEEDED"],["보호 가드","github-chat-v1 frozen / 전·후 PASS"]],[42*mm,128*mm]),
              Spacer(1,6*mm), p("롤백", "h2"), p("이전 Image ID와 DB Dump를 사용해 AI Gateway만 복원한다. Assist Flow 문제는 새 Flow 2개만 비활성화한다. 기존 GitHub→Chat Flow·Hook·Adapter·Ingress는 롤백 대상에도 포함하지 않는다."),
              p("8. 검토 포인트", "h1"), p("구현·실증 범위는 완료했다. 제품 책임자는 실제 기술지원 채널 Pilot 범위와 고객 공개 시점을 결정하면 된다. 공개 여부는 구현 범위를 제한하지 않는다."),
              p("자산", "h2"), p("설계, Runbook, OpenAPI, Golden Set, 합성 화면, Reference/Live Evaluation JSON, PDF, PPTX와 Manifest를 저장소에서 함께 관리한다.")]
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def build_slide_pdf():
    rendered = ROOT / "tmp/issues-56-58-slides/rendered"
    pages = sorted(rendered.glob("slide-*.png"))
    width, height = landscape(A4)
    pdf = canvas.Canvas(str(SLIDES), pagesize=(width, height))
    for page in pages:
        pdf.drawImage(str(page), 0, 0, width=width, height=height, preserveAspectRatio=True, anchor="c")
        pdf.showPage()
    pdf.save()


if __name__ == "__main__":
    build_report(); build_slide_pdf(); print(f"report={REPORT}\nslides={SLIDES}")
