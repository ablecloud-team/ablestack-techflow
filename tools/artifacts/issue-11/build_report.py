#!/usr/bin/env python3
"""Build the Issue #11 decision report PDF from the canonical JSON."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
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
DATA_PATH = ROOT / "docs" / "decisions" / "activepieces-license-review.json"
OUTPUT_PATH = ROOT / "output" / "pdf" / "activepieces-license-review-report.pdf"

BLUE = colors.HexColor("#3D8DFF")
LIGHT_BLUE = colors.HexColor("#DDF3FF")
PALE_BLUE = colors.HexColor("#F3FAFE")
BLACK = colors.HexColor("#111111")
GRAY_900 = colors.HexColor("#252525")
GRAY_700 = colors.HexColor("#555555")
GRAY_500 = colors.HexColor("#858585")
GRAY_300 = colors.HexColor("#D9D9D9")
GRAY_100 = colors.HexColor("#F2F2F2")
GREEN = colors.HexColor("#177245")
GREEN_BG = colors.HexColor("#E8F5ED")
AMBER = colors.HexColor("#8A5A00")
AMBER_BG = colors.HexColor("#FFF4D6")
RED = colors.HexColor("#A52714")
RED_BG = colors.HexColor("#FCE8E6")


def register_fonts() -> tuple[str, str]:
    regular = Path(r"C:\Windows\Fonts\malgun.ttf")
    bold = Path(r"C:\Windows\Fonts\malgunbd.ttf")
    if regular.exists() and bold.exists():
        pdfmetrics.registerFont(TTFont("Malgun", str(regular)))
        pdfmetrics.registerFont(TTFont("Malgun-Bold", str(bold)))
        return "Malgun", "Malgun-Bold"
    return "Helvetica", "Helvetica-Bold"


FONT, FONT_BOLD = register_fonts()


def esc(value: object) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def decision_label(value: str) -> str:
    labels = {
        "APPROVED": "승인",
        "APPROVED_WITH_SBOM": "SBOM 조건부 승인",
        "CONDITIONAL": "조건부",
        "COMMERCIAL_REQUIRED": "상용 계약 필요",
        "BLOCKED": "차단",
    }
    return labels.get(value, value)


def status_colors(value: str) -> tuple[colors.Color, colors.Color]:
    if value in {"APPROVED", "APPROVED_WITH_SBOM"}:
        return GREEN_BG, GREEN
    if value == "CONDITIONAL":
        return AMBER_BG, AMBER
    return RED_BG, RED


styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        "KBody",
        parent=styles["BodyText"],
        fontName=FONT,
        fontSize=9.5,
        leading=14.5,
        textColor=GRAY_900,
        spaceAfter=5,
        wordWrap="CJK",
    )
)
styles.add(
    ParagraphStyle(
        "KSmall",
        parent=styles["BodyText"],
        fontName=FONT,
        fontSize=7.7,
        leading=11.2,
        textColor=GRAY_700,
        wordWrap="CJK",
    )
)
styles.add(
    ParagraphStyle(
        "KTable",
        parent=styles["BodyText"],
        fontName=FONT,
        fontSize=7.2,
        leading=10.4,
        textColor=GRAY_900,
        wordWrap="CJK",
    )
)
styles.add(
    ParagraphStyle(
        "KTableHead",
        parent=styles["BodyText"],
        fontName=FONT_BOLD,
        fontSize=7.5,
        leading=10,
        textColor=colors.white,
        alignment=TA_LEFT,
        wordWrap="CJK",
    )
)
styles.add(
    ParagraphStyle(
        "KTitle",
        parent=styles["Title"],
        fontName=FONT_BOLD,
        fontSize=27,
        leading=34,
        textColor=BLACK,
        alignment=TA_LEFT,
        wordWrap="CJK",
    )
)
styles.add(
    ParagraphStyle(
        "KSubtitle",
        parent=styles["BodyText"],
        fontName=FONT,
        fontSize=12.5,
        leading=18,
        textColor=GRAY_700,
        wordWrap="CJK",
    )
)
styles.add(
    ParagraphStyle(
        "KH1",
        parent=styles["Heading1"],
        fontName=FONT_BOLD,
        fontSize=18,
        leading=23,
        textColor=BLACK,
        spaceBefore=4,
        spaceAfter=10,
        wordWrap="CJK",
    )
)
styles.add(
    ParagraphStyle(
        "KH2",
        parent=styles["Heading2"],
        fontName=FONT_BOLD,
        fontSize=12.5,
        leading=17,
        textColor=BLACK,
        spaceBefore=7,
        spaceAfter=6,
        wordWrap="CJK",
    )
)
styles.add(
    ParagraphStyle(
        "KCallout",
        parent=styles["BodyText"],
        fontName=FONT_BOLD,
        fontSize=12,
        leading=18,
        textColor=BLACK,
        wordWrap="CJK",
    )
)
styles.add(
    ParagraphStyle(
        "KCoverMeta",
        parent=styles["BodyText"],
        fontName=FONT,
        fontSize=9,
        leading=14,
        textColor=GRAY_700,
        wordWrap="CJK",
    )
)


def P(text: object, style: str = "KBody") -> Paragraph:
    return Paragraph(esc(text), styles[style])


def link(title: str, url: str) -> Paragraph:
    return Paragraph(
        f'<link href="{esc(url)}" color="#3D8DFF">{esc(title)}</link><br/>'
        f'<font size="7" color="#777777">{esc(url)}</font>',
        styles["KSmall"],
    )


def bullet(text: str) -> Paragraph:
    return Paragraph(f"• {esc(text)}", styles["KBody"])


def table(
    rows: list[list[object]],
    widths: list[float],
    *,
    header: bool = True,
    font_size: float = 7.2,
) -> Table:
    rendered: list[list[object]] = []
    for r, row in enumerate(rows):
        style_name = "KTableHead" if header and r == 0 else "KTable"
        rendered.append(
            [cell if isinstance(cell, Paragraph) else P(cell, style_name) for cell in row]
        )
    result = Table(rendered, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.35, GRAY_300),
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
    ]
    if header:
        commands += [
            ("BACKGROUND", (0, 0), (-1, 0), BLACK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ]
    for idx in range(1 if header else 0, len(rows)):
        if idx % 2 == 0:
            commands.append(("BACKGROUND", (0, idx), (-1, idx), PALE_BLUE))
    result.setStyle(TableStyle(commands))
    return result


def status_table(items: list[dict[str, str]]) -> Table:
    rows: list[list[object]] = [[P("시나리오", "KTableHead"), P("판단", "KTableHead"), P("조건", "KTableHead")]]
    for item in items:
        bg, fg = status_colors(item["status"])
        badge = Table(
            [[Paragraph(f"<b>{esc(decision_label(item['status']))}</b>", styles["KTable"])]],
            colWidths=[31 * mm],
        )
        badge.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), bg),
                    ("TEXTCOLOR", (0, 0), (-1, -1), fg),
                    ("BOX", (0, 0), (-1, -1), 0.4, fg),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        rows.append([P(item["name"], "KTable"), badge, P(item["conditions"], "KTable")])
    result = Table(rows, colWidths=[43 * mm, 35 * mm, 96 * mm], repeatRows=1)
    result.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BLACK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, GRAY_300),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return result


class DecisionDoc(BaseDocTemplate):
    def __init__(self, filename: str):
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=21 * mm,
            bottomMargin=18 * mm,
            title="Activepieces Community·Enterprise 기능 및 라이선스 검토",
            author="ABLESTACK TechFlow",
            subject="GitHub Issue #11",
        )
        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="normal",
        )
        self.addPageTemplates(PageTemplate(id="all", frames=frame, onPage=self._page))

    def _page(self, canvas, doc):
        if doc.page > 1:
            canvas.saveState()
            canvas.setStrokeColor(GRAY_300)
            canvas.setLineWidth(0.4)
            canvas.line(18 * mm, A4[1] - 14 * mm, A4[0] - 18 * mm, A4[1] - 14 * mm)
            canvas.setFont(FONT, 7)
            canvas.setFillColor(GRAY_500)
            canvas.drawString(18 * mm, A4[1] - 11 * mm, "ABLESTACK TechFlow · Issue #11")
            canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"{doc.page}")
            canvas.restoreState()


def build() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc = DecisionDoc(str(OUTPUT_PATH))
    story: list[object] = []

    story += [
        Spacer(1, 19 * mm),
        P("ABLESTACK TECHFLOW", "KCoverMeta"),
        Spacer(1, 5 * mm),
        Paragraph(
            "Activepieces Community·Enterprise<br/>기능 및 라이선스 검토",
            styles["KTitle"],
        ),
        Spacer(1, 7 * mm),
        P(
            "사내 Assist 실증부터 고객 제품화까지의 사용 범위, 대체 설계, 계약 게이트",
            "KSubtitle",
        ),
        Spacer(1, 22 * mm),
        Table(
            [
                [P("결정", "KTableHead"), P("사내 PoC 승인 · 고객 제품화 조건부", "KCallout")],
                [P("기준 버전", "KTableHead"), P(data["baseline"]["version"], "KBody")],
                [P("기준 커밋", "KTableHead"), P(data["baseline"]["tagCommit"], "KBody")],
                [P("검토일", "KTableHead"), P(data["analysisDate"], "KBody")],
                [P("GitHub Issue", "KTableHead"), P(f"#{data['issue']}", "KBody")],
            ],
            colWidths=[34 * mm, 131 * mm],
            style=[
                ("BACKGROUND", (0, 0), (0, -1), BLACK),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
                ("BACKGROUND", (1, 0), (1, 0), LIGHT_BLUE),
                ("GRID", (0, 0), (-1, -1), 0.5, GRAY_300),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ],
        ),
        Spacer(1, 25 * mm),
        P(data["legalDisclaimer"], "KSmall"),
        PageBreak(),
    ]

    story += [
        P("1. 경영 요약", "KH1"),
        P(data["executiveDecision"]["summary"], "KCallout"),
        Spacer(1, 5 * mm),
        status_table(data["scenarios"]),
        Spacer(1, 8 * mm),
        P("승인 요청", "KH2"),
        bullet("사내 Assist PoC는 Community 0.86.3과 사내 운영자 전용 UI로 착수한다."),
        bullet("고객 제품은 TechFlow가 권한·정책·승인·감사를 소유하는 구조로 구현한다."),
        bullet("고객 배포·직접 UI·Embedding·Platform API는 서면 확인 또는 상용 계약 전까지 차단한다."),
        PageBreak(),
    ]

    story += [P("2. 분석 기준과 라이선스 경계", "KH1")]
    baseline_rows = [
        ["항목", "값"],
        ["Release", data["baseline"]["version"]],
        ["Release date", data["baseline"]["releaseDate"]],
        ["Tag commit", data["baseline"]["tagCommit"]],
        ["Root LICENSE SHA-256", data["baseline"]["rootLicenseSha256"]],
        ["Enterprise LICENSE SHA-256", data["baseline"]["enterpriseLicenseSha256"]],
    ]
    story += [table(baseline_rows, [45 * mm, 129 * mm]), Spacer(1, 7 * mm)]
    boundary_rows = [["영역", "범위", "조건", "TechFlow 판단"]]
    for item in data["licenseBoundary"]:
        boundary_rows.append([item["area"], item["scope"], item["terms"], item["decision"]])
    story += [
        table(boundary_rows, [28 * mm, 53 * mm, 36 * mm, 57 * mm]),
        Spacer(1, 7 * mm),
        P(
            "Community 자체 코드의 MIT 권리와 Enterprise 코드·제3자 구성요소의 권리를 분리해서 판단해야 한다. "
            "공식 결합 이미지의 고객 재배포는 저장소 MIT 고지만으로 확정하지 않고 Activepieces의 서면 답변을 제품 출시 게이트로 둔다.",
            "KBody",
        ),
        PageBreak(),
    ]

    story += [P("3. 기능 매트릭스", "KH1")]
    feature_rows = [["기능", "단계", "Edition", "판단", "TechFlow 적용·대안"]]
    for feature in data["featureMatrix"]:
        feature_rows.append(
            [
                feature["capability"],
                feature["phase"],
                feature["edition"],
                decision_label(feature["decision"]),
                f"{feature['use']} / {feature['alternative']}",
            ]
        )
    story += [
        table(feature_rows, [39 * mm, 16 * mm, 26 * mm, 29 * mm, 64 * mm], font_size=6.8),
        PageBreak(),
    ]

    story += [P("4. 제품 아키텍처와 권한 경계", "KH1")]
    architecture_rows = [["소유자", "책임"]]
    for item in data["architectureBoundaries"]:
        architecture_rows.append([item["owner"], item["responsibilities"]])
    story += [
        table(architecture_rows, [48 * mm, 126 * mm]),
        Spacer(1, 8 * mm),
        P("핵심 설계 원칙", "KH2"),
        bullet("Activepieces는 실행 엔진이지 TechFlow의 권한 경계가 아니다."),
        bullet("TechFlow 입력은 서명 Webhook, 출력은 Custom Piece callback 또는 TechFlow 소유 API를 기본으로 한다."),
        bullet("사내 PoC에서 Activepieces Platform API Key 기능을 사용하지 않는다."),
        bullet("가상자원 변경의 최종 권한·상태·멱등성은 ABLESTACK/Mold API가 보장한다."),
        Spacer(1, 7 * mm),
        Table(
            [
                [P("채널", "KTableHead"), P("TechFlow Core", "KTableHead"), P("Activepieces", "KTableHead"), P("ABLESTACK API", "KTableHead")],
                [P("GitHub · Community · Messenger", "KTable"), P("인증 · 정책 · 승인 · 감사 · AI/RAG", "KTable"), P("Flow · Queue · Worker · Retry", "KTable"), P("권한 · 최종 상태 · 실제 작업", "KTable")],
            ],
            colWidths=[38 * mm, 55 * mm, 43 * mm, 38 * mm],
            style=[
                ("BACKGROUND", (0, 0), (-1, 0), BLACK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (0, 1), GRAY_100),
                ("BACKGROUND", (1, 1), (1, 1), LIGHT_BLUE),
                ("BACKGROUND", (2, 1), (2, 1), PALE_BLUE),
                ("BACKGROUND", (3, 1), (3, 1), GRAY_100),
                ("GRID", (0, 0), (-1, -1), 0.5, GRAY_300),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ],
        ),
        PageBreak(),
    ]

    story += [P("5. 제품 출시 게이트", "KH1")]
    gate_rows = [["게이트", "허용 범위", "완료 기준"]]
    for gate in data["releaseGates"]:
        gate_rows.append([f"{gate['id']} {gate['name']}", gate["name"].replace(" 허용", ""), gate["criteria"]])
    story += [
        table(gate_rows, [42 * mm, 39 * mm, 93 * mm]),
        Spacer(1, 9 * mm),
        P("제3자 라이선스·공급망 필수 절차", "KH2"),
        bullet("정확한 컨테이너 이미지 digest를 고정한다."),
        bullet("이미지와 애플리케이션 SBOM을 SPDX 또는 CycloneDX로 생성한다."),
        bullet("라이선스 탐지 결과·수동 예외·NOTICE를 릴리스 증적과 함께 보관한다."),
        bullet("copyleft·source-available·unknown 항목은 고객 배포 전에 법무가 승인한다."),
        bullet("버전 변경 때마다 SBOM과 라이선스 차이를 다시 검토한다."),
        PageBreak(),
    ]

    story += [P("6. Activepieces 서면 확인 질문", "KH1")]
    for idx, question in enumerate(data["vendorQuestions"], start=1):
        story.append(P(f"{idx}. {question}", "KBody"))
    story += [
        Spacer(1, 6 * mm),
        P("질문에 대한 서면 답변은 G2 고객 파일럿의 필수 증적이다.", "KCallout"),
        PageBreak(),
    ]

    story += [P("7. 완료 기준과 후속 작업", "KH1")]
    completed = [
        "Community·Enterprise·제3자 라이선스 경계 확인",
        "기능별 사용 범위와 대체 설계 작성",
        "사내 PoC·고객 배포·임베딩·SaaS·오프라인 시나리오 판단",
        "TechFlow와 Activepieces 권한 경계 확정",
        "고객 제품화 단계별 게이트 정의",
        "벤더 서면 확인 질문 작성",
        "JSON 원본, 보고서 PDF, 프레젠테이션 PPTX·PDF 생성 체계 구성",
    ]
    for item in completed:
        story.append(P(f"✓ {item}", "KBody"))
    story += [
        Spacer(1, 5 * mm),
        P("후속 고객 출시 게이트", "KH2"),
        bullet("Activepieces 서면 답변 수령과 법무 승인"),
        bullet("최종 배포 이미지 SBOM·NOTICE·취약점·라이선스 예외 검토"),
        bullet("고객별 설치·백업·업그레이드·롤백·보안 통지 운영 절차 확정"),
        PageBreak(),
    ]

    story += [P("8. 공식 근거", "KH1")]
    for source in data["sources"]:
        story += [link(f"{source['id']} · {source['title']} — {source['purpose']}", source["url"]), Spacer(1, 2 * mm)]
    story += [
        Spacer(1, 7 * mm),
        P(data["legalDisclaimer"], "KSmall"),
    ]

    doc.build(story)
    print(OUTPUT_PATH)


if __name__ == "__main__":
    try:
        build()
    except Exception as exc:
        print(f"report build failed: {exc}", file=sys.stderr)
        raise
