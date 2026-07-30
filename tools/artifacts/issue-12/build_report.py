from __future__ import annotations

import json
from pathlib import Path
from xml.sax.saxutils import escape

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
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[3]
DATA_PATH = (
    ROOT / "docs" / "decisions" / "techflow-activepieces-responsibility-boundary.json"
)
OUTPUT_PATH = ROOT / "output" / "pdf" / "techflow-responsibility-boundary-report.pdf"

FONT = "MalgunGothic"
FONT_BOLD = "MalgunGothicBold"
pdfmetrics.registerFont(TTFont(FONT, "C:/Windows/Fonts/malgun.ttf"))
pdfmetrics.registerFont(TTFont(FONT_BOLD, "C:/Windows/Fonts/malgunbd.ttf"))

BLACK = colors.HexColor("#111111")
GRAY_700 = colors.HexColor("#4B5563")
GRAY_500 = colors.HexColor("#6B7280")
GRAY_300 = colors.HexColor("#D1D5DB")
GRAY_100 = colors.HexColor("#F3F4F6")
BLUE = colors.HexColor("#3B82F6")
LIGHT_BLUE = colors.HexColor("#D9F0FC")
PALE_BLUE = colors.HexColor("#EEF8FD")
GREEN = colors.HexColor("#117A4B")
PALE_GREEN = colors.HexColor("#E8F5EE")
AMBER = colors.HexColor("#8A5A00")
PALE_AMBER = colors.HexColor("#FFF3D6")
RED = colors.HexColor("#B42318")
PALE_RED = colors.HexColor("#FDE9E7")

base_styles = getSampleStyleSheet()
styles = {
    "cover_meta": ParagraphStyle(
        "cover_meta",
        parent=base_styles["Normal"],
        fontName=FONT,
        fontSize=10,
        leading=14,
        textColor=GRAY_700,
    ),
    "title": ParagraphStyle(
        "title",
        parent=base_styles["Title"],
        fontName=FONT_BOLD,
        fontSize=29,
        leading=38,
        textColor=BLACK,
        alignment=TA_LEFT,
        spaceAfter=0,
    ),
    "subtitle": ParagraphStyle(
        "subtitle",
        parent=base_styles["Normal"],
        fontName=FONT,
        fontSize=14,
        leading=21,
        textColor=GRAY_700,
    ),
    "h1": ParagraphStyle(
        "h1",
        parent=base_styles["Heading1"],
        fontName=FONT_BOLD,
        fontSize=20,
        leading=27,
        textColor=BLACK,
        spaceAfter=7 * mm,
    ),
    "h2": ParagraphStyle(
        "h2",
        parent=base_styles["Heading2"],
        fontName=FONT_BOLD,
        fontSize=13,
        leading=19,
        textColor=BLACK,
        spaceBefore=4 * mm,
        spaceAfter=3 * mm,
    ),
    "body": ParagraphStyle(
        "body",
        parent=base_styles["BodyText"],
        fontName=FONT,
        fontSize=9.5,
        leading=15,
        textColor=colors.HexColor("#2F3136"),
        spaceAfter=2 * mm,
    ),
    "small": ParagraphStyle(
        "small",
        parent=base_styles["BodyText"],
        fontName=FONT,
        fontSize=7.5,
        leading=11,
        textColor=GRAY_500,
    ),
    "callout": ParagraphStyle(
        "callout",
        parent=base_styles["BodyText"],
        fontName=FONT_BOLD,
        fontSize=11.5,
        leading=18,
        textColor=BLACK,
    ),
    "table": ParagraphStyle(
        "table",
        parent=base_styles["BodyText"],
        fontName=FONT,
        fontSize=7.7,
        leading=11,
        textColor=colors.HexColor("#30343B"),
    ),
    "table_head": ParagraphStyle(
        "table_head",
        parent=base_styles["BodyText"],
        fontName=FONT_BOLD,
        fontSize=7.7,
        leading=11,
        textColor=colors.white,
    ),
    "badge": ParagraphStyle(
        "badge",
        parent=base_styles["BodyText"],
        fontName=FONT_BOLD,
        fontSize=8,
        leading=11,
        textColor=GREEN,
        alignment=TA_CENTER,
    ),
}


def p(text: object, style: str = "body") -> Paragraph:
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), styles[style])


def bullet(text: str) -> Paragraph:
    return Paragraph(
        f"• {escape(text)}",
        ParagraphStyle(
            "bullet_local",
            parent=styles["body"],
            leftIndent=4 * mm,
            firstLineIndent=-3 * mm,
            spaceAfter=2 * mm,
        ),
    )


def make_table(
    rows: list[list[object]],
    widths: list[float],
    *,
    header: bool = True,
    font_size: float = 7.7,
) -> Table:
    body_style = ParagraphStyle(
        f"table_{font_size}",
        parent=styles["table"],
        fontSize=font_size,
        leading=font_size * 1.45,
    )
    converted: list[list[Paragraph]] = []
    for row_index, row in enumerate(rows):
        style = styles["table_head"] if header and row_index == 0 else body_style
        converted.append(
            [Paragraph(escape(str(value)).replace("\n", "<br/>"), style) for value in row]
        )
    result = Table(converted, colWidths=widths, repeatRows=1 if header else 0)
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.35, GRAY_300),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        commands.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BLACK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ]
        )
        start = 1
    else:
        start = 0
    for row_index in range(start, len(rows)):
        if row_index % 2 == 0:
            commands.append(("BACKGROUND", (0, row_index), (-1, row_index), PALE_BLUE))
    result.setStyle(TableStyle(commands))
    return result


class AdrDocument(BaseDocTemplate):
    def __init__(self, filename: str):
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=21 * mm,
            bottomMargin=18 * mm,
            title="TechFlow와 Activepieces 책임 경계 ADR",
            author="ABLESTACK TechFlow",
            subject="GitHub Issue #12",
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
        if doc.page <= 1:
            return
        canvas.saveState()
        canvas.setStrokeColor(GRAY_300)
        canvas.setLineWidth(0.4)
        canvas.line(18 * mm, A4[1] - 14 * mm, A4[0] - 18 * mm, A4[1] - 14 * mm)
        canvas.setFont(FONT, 7)
        canvas.setFillColor(GRAY_500)
        canvas.drawString(18 * mm, A4[1] - 11 * mm, "ABLESTACK TechFlow · ADR-0001 · Issue #12")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"{doc.page}")
        canvas.restoreState()


def build() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc = AdrDocument(str(OUTPUT_PATH))
    story: list[object] = []

    story.extend(
        [
            Spacer(1, 22 * mm),
            p("ABLESTACK TECHFLOW", "cover_meta"),
            Spacer(1, 6 * mm),
            Paragraph("TechFlow와 Activepieces<br/>책임 경계 ADR", styles["title"]),
            Spacer(1, 8 * mm),
            p("권한·상태·멱등성·실패를 세 계층으로 분리", "subtitle"),
            Spacer(1, 25 * mm),
            Table(
                [
                    [p("결정", "table_head"), p("세 계층 책임 분리", "callout")],
                    [p("ADR", "table_head"), p(data["adr"])],
                    [p("상태", "table_head"), p(data["status"].upper())],
                    [p("결정일", "table_head"), p(data["decisionDate"])],
                    [p("GitHub Issue", "table_head"), p(f"#{data['issue']}")],
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
            Spacer(1, 24 * mm),
            p(
                "비밀번호, 토큰, API 키, 개인정보와 내부 로그 원문은 이 문서와 산출물에 포함하지 않는다. "
                "민감정보는 승인된 저장소와 런타임 주입으로만 처리한다.",
                "small",
            ),
            PageBreak(),
        ]
    )

    story.extend([p("1. 결정 요약", "h1"), p(data["summary"], "callout"), Spacer(1, 6 * mm)])
    component_rows = [["계층", "소유 책임", "권위 상태", "금지사항"]]
    for component in data["components"]:
        component_rows.append(
            [
                component["name"],
                "\n".join(component["owns"]),
                "\n".join(component["authoritativeState"]),
                "\n".join(component["mustNot"]),
            ]
        )
    story.extend(
        [
            make_table(
                component_rows,
                [32 * mm, 55 * mm, 38 * mm, 49 * mm],
                font_size=6.9,
            ),
            Spacer(1, 7 * mm),
            p(
                "핵심 판정: Activepieces의 FlowRun 성공은 실제 자원 작업의 성공 근거가 아니다. "
                "TechFlow Core는 ABLESTACK API의 Operation과 ResourceState를 재조회한 뒤 결과를 확정한다.",
                "callout",
            ),
            PageBreak(),
        ]
    )

    story.extend([p("2. 실행 명령과 수명주기", "h1")])
    story.extend([p("ExecutionCommand 필수 필드", "h2")])
    story.append(p(", ".join(data["executionEnvelope"]["requiredFields"])))
    story.extend([p("명령 계약 규칙", "h2")])
    for rule in data["executionEnvelope"]["rules"]:
        story.append(bullet(rule))
    lifecycle_rows = [["단계", "소유자", "동작", "결과"]]
    for item in data["lifecycle"]:
        lifecycle_rows.append(
            [item["step"], item["owner"], item["action"], item["result"]]
        )
    story.extend(
        [
            Spacer(1, 5 * mm),
            make_table(lifecycle_rows, [13 * mm, 35 * mm, 86 * mm, 40 * mm], font_size=7.2),
            PageBreak(),
        ]
    )

    story.extend([p("3. 상태와 두 단계 멱등성", "h1")])
    state_rows = [["소유자", "모델", "상태", "최종 상태·판정"]]
    for model in data["stateModels"]:
        state_rows.append(
            [
                model["owner"],
                model["model"],
                "\n".join(model["states"]),
                "\n".join(model["terminalStates"]) + ("\n" + model.get("note", "") if model.get("note") else ""),
            ]
        )
    story.extend(
        [
            make_table(state_rows, [35 * mm, 33 * mm, 53 * mm, 53 * mm], font_size=7.1),
            Spacer(1, 8 * mm),
            p("두 단계 멱등성", "h2"),
            make_table(
                [
                    ["계층", "대상", "키", "보장"],
                    ["TechFlow Core", "제품 요청", "이벤트 ID · requestId · 요청 지문", "중복 요청이 새 승인·명령을 만들지 않음"],
                    ["ABLESTACK API", "인프라 작업", "commandId · idempotencyKey · 명령 지문", "전송 재시도에도 실제 작업을 한 번만 생성"],
                ],
                [35 * mm, 31 * mm, 55 * mm, 53 * mm],
            ),
            Spacer(1, 7 * mm),
            p("같은 멱등성 키와 다른 명령 지문은 충돌로 거부한다.", "callout"),
            PageBreak(),
        ]
    )

    story.extend([p("4. 실패 경계", "h1")])
    failure_rows = [["장애", "책임 계층", "필수 동작", "금지 동작"]]
    for item in data["failureBoundaries"]:
        failure_rows.append(
            [
                item["failure"],
                item["owner"],
                item["requiredBehavior"],
                item["forbiddenBehavior"],
            ]
        )
    story.extend(
        [
            make_table(failure_rows, [36 * mm, 34 * mm, 62 * mm, 42 * mm], font_size=7.2),
            Spacer(1, 8 * mm),
            p(
                "Timeout, 5xx, 연결 종료와 Callback 유실은 성공 또는 실패로 추정하지 않는다. "
                "VERIFYING 또는 UNKNOWN으로 유지하고 권위 상태를 조회한다.",
                "callout",
            ),
            PageBreak(),
        ]
    )

    story.extend([p("5. 재시도와 보안", "h1"), p("재시도 분류", "h2")])
    retry_rows = [["분류", "예", "규칙"]]
    for item in data["retryPolicy"]:
        retry_rows.append([item["class"], item["examples"], item["rule"]])
    story.extend(
        [
            make_table(retry_rows, [39 * mm, 55 * mm, 80 * mm]),
            Spacer(1, 9 * mm),
            p("보안 통제", "h2"),
        ]
    )
    for control in data["securityControls"]:
        story.append(bullet(control))
    story.extend(
        [
            Spacer(1, 5 * mm),
            p("자원 변경은 감사 이벤트 영속화 성공 후에만 발행하며 Secret 장애는 Fail Closed한다.", "callout"),
            PageBreak(),
        ]
    )

    story.extend([p("6. 테스트 요구사항", "h1")])
    test_rows = [["ID", "유형", "시나리오", "통과 기준"]]
    for test in data["testRequirements"]:
        test_rows.append([test["id"], test["type"], test["scenario"], test["pass"]])
    story.extend(
        [
            make_table(test_rows, [13 * mm, 23 * mm, 67 * mm, 71 * mm], font_size=7.2),
            Spacer(1, 8 * mm),
            p(
                "핵심 품질 게이트: Blind Retry 0건, 중복 작업 0건, 승인 변조 차단, "
                "요청부터 자원 최종 상태까지 감사 재구성 가능.",
                "callout",
            ),
            PageBreak(),
        ]
    )

    story.extend([p("7. 운영과 구현 규칙", "h1"), p("운영 규칙", "h2")])
    for item in data["operations"]:
        story.append(bullet(item))
    story.extend([Spacer(1, 5 * mm), p("구현 규칙", "h2")])
    for item in data["implementationRules"]:
        story.append(bullet(item))
    story.extend(
        [
            Spacer(1, 5 * mm),
            p(
                "후속 Core, Custom Piece와 ABLESTACK API 이슈는 ADR-0001을 참조하고 "
                "해당 경계를 변경할 때 새 ADR 또는 명시적 개정 승인을 요구한다.",
                "callout",
            ),
            PageBreak(),
        ]
    )

    story.extend([p("8. 결과와 완료 기준", "h1"), p("수용하는 결과", "h2")])
    consequence_rows = [
        ["구분", "결과"],
        ["제품 독립성", "실행 엔진 교체·업그레이드가 제품 권한 모델을 변경하지 않는다."],
        ["안전성", "중복 이벤트·재시도에도 실제 자원 작업을 한 번만 생성한다."],
        ["복구성", "Timeout·부분 실패에서 권위 상태 조회와 Reconcile로 수렴한다."],
        ["추적성", "고객·테넌트 정책, 승인과 감사가 TechFlow 제품 자산으로 유지된다."],
        ["구현 비용", "요청 원장, 명령 발행, Reconciler, API 멱등성과 엄격한 Piece 계약이 필요하다."],
    ]
    story.extend([make_table(consequence_rows, [35 * mm, 139 * mm]), Spacer(1, 9 * mm), p("완료 기준", "h2")])
    for criterion in data["completionCriteria"]:
        story.append(bullet(criterion))
    story.extend(
        [
            Spacer(1, 5 * mm),
            p("ADR-0001 상태: ACCEPTED", "callout"),
            PageBreak(),
        ]
    )

    story.extend([p("9. 근거와 추적성", "h1")])
    reference_rows = [["ID", "자료", "위치"]]
    for reference in data["references"]:
        reference_rows.append([reference["id"], reference["title"], reference["path"]])
    story.extend(
        [
            make_table(reference_rows, [16 * mm, 62 * mm, 96 * mm]),
            Spacer(1, 10 * mm),
            p("산출물 추적 규칙", "h2"),
            bullet("구조화된 JSON을 보고서와 발표자료의 내용 원본으로 사용한다."),
            bullet("ADR 변경 시 JSON, README, 로드맵, PDF, PPTX와 매니페스트를 함께 갱신한다."),
            bullet("산출물 해시는 output/issue-12-artifact-manifest.json에 기록한다."),
            bullet("민감정보 검사와 Markdown 링크 검증을 PR 완료 전에 수행한다."),
            Spacer(1, 10 * mm),
            p(
                "이 문서는 ABLESTACK TechFlow의 구현 경계를 확정하는 아키텍처 결정이다. "
                "고객 공개·판매·배포 판단은 이 ADR의 구현 규칙과 분리한다.",
                "callout",
            ),
        ]
    )

    doc.build(story)
    print(OUTPUT_PATH)


if __name__ == "__main__":
    build()
