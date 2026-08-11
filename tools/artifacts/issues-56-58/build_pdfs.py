#!/usr/bin/env python3
"""Build the Issues #56-#58 validation report and presentation PDF."""

from __future__ import annotations

import html
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
    for path in (Path("C:/Windows/Fonts/malgun.ttf"), Path("C:/Windows/Fonts/arial.ttf")):
        if path.exists():
            pdfmetrics.registerFont(TTFont("TechFlow", str(path)))
            return "TechFlow"
    return "Helvetica"


FONT = register_font()
BLUE = colors.HexColor("#17365D")
LIGHT = colors.HexColor("#EEF4FA")
GRID = colors.HexColor("#9AA7B4")


def styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"], fontName=FONT, fontSize=26, leading=34, textColor=BLUE, alignment=TA_LEFT, spaceAfter=12),
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName=FONT, fontSize=18, leading=24, textColor=BLUE, spaceBefore=4, spaceAfter=9),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName=FONT, fontSize=13, leading=18, textColor=BLUE, spaceBefore=6, spaceAfter=5),
        "body": ParagraphStyle("body", parent=base["BodyText"], fontName=FONT, fontSize=9.4, leading=15, wordWrap="CJK", spaceAfter=5),
        "small": ParagraphStyle("small", parent=base["BodyText"], fontName=FONT, fontSize=7.2, leading=10.5, wordWrap="CJK"),
        "cover": ParagraphStyle("cover", parent=base["Title"], fontName=FONT, fontSize=29, leading=40, textColor=colors.white, alignment=TA_CENTER),
        "cover_sub": ParagraphStyle("cover_sub", parent=base["BodyText"], fontName=FONT, fontSize=13, leading=20, textColor=colors.white, alignment=TA_CENTER),
    }


S = styles()


def p(value: object, style: str = "body") -> Paragraph:
    text = html.escape(str(value)).replace("\n", "<br/>")
    return Paragraph(text, S[style])


def table(rows, widths, *, header=True):
    result = Table([[p(cell, "small") for cell in row] for row in rows], colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, GRID),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        commands.extend([("BACKGROUND", (0, 0), (-1, 0), BLUE), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white)])
    result.setStyle(TableStyle(commands))
    return result


def footer(pdf, doc):
    pdf.saveState()
    pdf.setFont(FONT, 7)
    pdf.setFillColor(colors.HexColor("#65758B"))
    pdf.drawString(18 * mm, 10 * mm, "ABLESTACK TechFlow · Issues #56~#58")
    pdf.drawRightString(192 * mm, 10 * mm, str(doc.page))
    pdf.restoreState()


def build_report():
    OUT.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(REPORT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title="TechFlow Assist 종합·멀티모달·로그 완료 보고",
    )
    story = []
    cover = Table(
        [[p("ABLESTACK TechFlow", "cover_sub")], [p("Assist 종합·멀티모달·로그\n완료 보고", "cover")], [p("Issues #56~#58 · 2026-08-11", "cover_sub")]],
        colWidths=[174 * mm], rowHeights=[30 * mm, 110 * mm, 40 * mm],
    )
    cover.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), BLUE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.extend([cover, PageBreak()])

    story.extend([
        p("1. 완료 요약", "h1"),
        p("종합 질문, 이미지, 일반 로그와 압축 로그를 하나의 ABLESTACK 근거 보고서로 합성하는 경로를 구현했다. Activepieces는 Artifact ID와 실행 순서만 전달하고, AI Gateway가 범위·호환성·압축 보안·비밀 마스킹·근거 검증·보류를 소유한다."),
        table([
            ["항목", "결과"],
            ["AI Gateway", "0.8.0 · OpenAI · running/healthy"],
            ["자동 시험", "131/131 PASS"],
            ["Golden Set", "종합 15 + 이미지 12 + 로그 12 = 39/39 PASS"],
            ["실서버", "일반 로그·ZIP 로그·경로 탈출 차단 PASS"],
            ["Activepieces", "Assist Flow 2개 ENABLED · E2E Run SUCCEEDED"],
            ["보호 서비스", "github-chat-v1 frozen · 배포 전후 가드 PASS"],
        ], [45 * mm, 125 * mm]),
        Spacer(1, 5 * mm),
        p("결론", "h2"),
        p("사용자는 질문과 화면 또는 지원 로그 묶음을 함께 제공할 수 있다. 답변은 소스 Citation과 Artifact의 파일·행 구간을 분리해 제시하며, 근거가 부족하면 추정 대신 ABSTAINED 또는 NEEDS_INFORMATION을 반환한다."),
        PageBreak(),
    ])

    story.extend([
        p("2. 아키텍처와 책임 경계", "h1"),
        table([
            ["단계", "소유자", "정책"],
            ["수신·실행", "Activepieces", "Webhook·Correlation·순차 HTTP; 파일 바이트 미보관"],
            ["범위 계획", "Planner", "영역·Cloud 브랜치가 불명확하면 Provider 호출 전 중단"],
            ["호환성", "Resolver", "복수 저장소는 승인된 Compatibility Set만 사용"],
            ["검색", "AI Gateway", "활성 Source Version의 고정 Commit 문서·소스 검색"],
            ["이미지", "Artifact Store", "D0·매직 바이트·크기·해상도 검증"],
            ["로그·압축", "Log Normalizer", "메모리 내 제한 해제·마스킹·오류 구간·행 번호 생성"],
            ["합성", "Responses Adapter", "strict JSON, 정확한 Evidence ID, 근거 부족 시 보류"],
        ], [31 * mm, 42 * mm, 97 * mm]),
        Spacer(1, 5 * mm),
        p("OpenAI 경계", "h2"),
        p("이미지는 input_image(detail=original)로 전달한다. 로그와 Archive는 원본 File Input으로 보내지 않는다. Gateway가 먼저 검증·해제·비밀 마스킹·구간 선별을 수행하고 `@@ member/path.log:10-14` 형태의 제한된 input_text만 전달한다. tools=[], store=false, background=false와 strict JSON Schema를 강제한다."),
        p("공식 참고: https://developers.openai.com/api/docs/guides/file-inputs · https://developers.openai.com/api/docs/guides/images-vision"),
        PageBreak(),
    ])

    screen = ROOT / "services/ai-gateway/app/data/golden-artifacts/synthetic-vm-error.png"
    story.extend([
        p("3. 이미지와 로그 Artifact 정책", "h1"),
        Image(str(screen), width=142 * mm, height=85.2 * mm),
        Spacer(1, 3 * mm),
        table([
            ["정책", "구현"],
            ["분류·형식", "D0 · PNG/JPEG/WebP · UTF-8 Log/Text/JSON/NDJSON/CSV/TSV · ZIP/GZIP/TAR.GZ/TGZ"],
            ["크기", "업로드 10 MiB · 압축 해제 합계 20 MiB · 질문당 5개"],
            ["Archive", "100 Member · 20:1 · 경로 탈출·Link·암호화·중첩·특수 파일 금지"],
            ["로그 근거", "ERROR/FATAL/Exception/WARN 주변 ±2행 · Artifact당 120,000자"],
            ["비밀", "Authorization·Password·Secret·Token·API Key를 [REDACTED]"],
            ["보존", "기본 24시간 · 디렉터리 0700 · 파일 0600 · 명시 삭제 후 404"],
        ], [39 * mm, 131 * mm]),
        PageBreak(),
    ])

    story.append(p("4. 실서버 질문·답변·판정", "h1"))
    for case in LIVE["cases"]:
        artifact_evidence = case.get("artifactEvidence")
        evidence = ""
        if artifact_evidence:
            evidence = f"\n근거: {json.dumps(artifact_evidence, ensure_ascii=False)}"
        story.append(KeepTogether([
            p(f"{case['caseId']} · {case['state']}", "h2"),
            p(f"질문: {case['question']}"),
            p(f"답변: {case.get('answer') or '응답 본문 없음'}{evidence}"),
            p(f"판정: {case['judgment']} · {case['reason']}"),
            Spacer(1, 2 * mm),
        ]))
    story.append(PageBreak())

    story.extend([
        p("5. Golden Question 39건", "h1"),
        p("각 행은 질문, 제품이 반환해야 하는 허용 응답, 판정 기준과 결과를 함께 보존한다. 실제 Provider 원문은 운영 DB에 저장하지 않는다."),
    ])
    golden_rows = [["ID", "유형", "질문", "허용 응답", "판정"]]
    for item in EVAL["results"]:
        golden_rows.append([item["caseId"], item["type"], item["question"], item["response"], item["judgment"]])
    story.extend([table(golden_rows, [17 * mm, 23 * mm, 62 * mm, 57 * mm, 15 * mm]), PageBreak()])

    story.extend([
        p("6. 시험 중 발견과 보완", "h1"),
        table([
            ["발견", "보완", "결과"],
            ["12초 Responses 읽기 제한", "연결 3초·읽기 90초·재시도 1회", "다중 저장소·이미지 생성 성공"],
            ["Artifact ID를 모델이 임의 생성", "허용 Evidence ID와 Manifest를 명시하고 계약 실패 시 1회 재시도", "정확한 ID·행 구간 반환"],
            ["고추론 ZIP 분석이 2,400토큰에서 불완전 종료", "종합 출력 예산을 5,000토큰으로 확대", "일반 로그·ZIP 모두 PASS"],
        ], [54 * mm, 72 * mm, 44 * mm]),
        Spacer(1, 5 * mm),
        p("최종 서버 증적", "h2"),
        table([
            ["항목", "값"],
            ["Image ID", LIVE["gateway"]["imageId"]],
            ["Health", "running/healthy · Process/Database/Vector ready · Provider openai"],
            ["Root Disk", "1005G · 25G 사용 · 939G 가용 · 3%"],
            ["Artifact Volume", "0700 · UID/GID 10001 · 시험 후 잔여 파일 0"],
            ["백업", LIVE["backup"]],
            ["보호 가드", "protected_service=github-chat-v1 state=frozen guard=passed"],
        ], [40 * mm, 130 * mm]),
        PageBreak(),
    ])

    story.extend([
        p("7. 롤백·자산·검토", "h1"),
        p("Gateway 장애 시 백업된 이전 Image ID와 DB Dump로 Gateway만 복원한다. Assist Flow 문제는 신규 Flow만 비활성화한다. GitHub→Chat의 Hook, Flow, Adapter, Ingress, SSRF Allowlist는 롤백·변경 대상에 포함하지 않는다."),
        table([
            ["자산", "경로"],
            ["설계", "docs/plans/issues-56-58-assist-multimodal-design.md"],
            ["Runbook", "docs/runbooks/assist-multimodal.md"],
            ["완료 보고", "docs/reports/issues-56-58-assist-multimodal-validation.md"],
            ["Golden 결과", "output/issues-56-58-reference-evaluation.json"],
            ["실서버 결과", "output/issues-56-58-live-evaluation.json"],
            ["OpenAPI", "services/ai-gateway/openapi/techflow-ai-gateway-v1.json"],
            ["발표자료", "output/presentation/techflow-assist-multimodal.pptx"],
        ], [41 * mm, 129 * mm]),
        Spacer(1, 5 * mm),
        p("검토 요청", "h2"),
        p("구현·시험·배포·복구 자산화는 완료됐다. 제품 책임자는 PR #59의 구현 범위와 실제 지원 채널 Pilot 범위를 검토하면 된다. 고객 공개 여부와 최종 제품화 여부는 별도 제품 결정이다."),
    ])
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
    build_report()
    build_slide_pdf()
    print(f"report={REPORT}\nslides={SLIDES}")
