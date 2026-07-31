#!/usr/bin/env python3
"""Build the Issue #18 immutable release validation report PDF."""

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
DATA_PATH = ROOT / "docs" / "decisions" / "techflow-image-version-lock.json"
OUTPUT_PATH = ROOT / "output" / "pdf" / "techflow-image-version-lock-report.pdf"

FONT = "MalgunGothic"
FONT_BOLD = "MalgunGothicBold"
pdfmetrics.registerFont(TTFont(FONT, "C:/Windows/Fonts/malgun.ttf"))
pdfmetrics.registerFont(TTFont(FONT_BOLD, "C:/Windows/Fonts/malgunbd.ttf"))

BLACK = colors.HexColor("#111111")
GRAY_700 = colors.HexColor("#4B5563")
GRAY_500 = colors.HexColor("#6B7280")
GRAY_300 = colors.HexColor("#D1D5DB")
BLUE = colors.HexColor("#2563EB")
PALE_BLUE = colors.HexColor("#EFF6FF")
GREEN = colors.HexColor("#117A4B")
PALE_GREEN = colors.HexColor("#E8F5EE")
AMBER = colors.HexColor("#8A5A00")
PALE_AMBER = colors.HexColor("#FFF7E6")

base = getSampleStyleSheet()
styles = {
    "meta": ParagraphStyle("meta", parent=base["Normal"], fontName=FONT, fontSize=10, leading=14, textColor=GRAY_700),
    "title": ParagraphStyle("title", parent=base["Title"], fontName=FONT_BOLD, fontSize=27, leading=38, textColor=BLACK),
    "subtitle": ParagraphStyle("subtitle", parent=base["Normal"], fontName=FONT, fontSize=14, leading=21, textColor=GRAY_700),
    "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName=FONT_BOLD, fontSize=20, leading=27, textColor=BLACK, spaceAfter=6 * mm),
    "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName=FONT_BOLD, fontSize=13, leading=19, textColor=BLACK, spaceBefore=4 * mm, spaceAfter=3 * mm),
    "body": ParagraphStyle("body", parent=base["BodyText"], fontName=FONT, fontSize=9.2, leading=14.5, textColor=colors.HexColor("#2F3136"), spaceAfter=2 * mm),
    "small": ParagraphStyle("small", parent=base["BodyText"], fontName=FONT, fontSize=7.4, leading=10.5, textColor=GRAY_500),
    "callout": ParagraphStyle("callout", parent=base["BodyText"], fontName=FONT_BOLD, fontSize=11, leading=17, textColor=BLACK),
    "table": ParagraphStyle("table", parent=base["BodyText"], fontName=FONT, fontSize=7.4, leading=10.5, textColor=colors.HexColor("#30343B")),
    "table_head": ParagraphStyle("table_head", parent=base["BodyText"], fontName=FONT_BOLD, fontSize=7.4, leading=10.5, textColor=colors.white),
}


def p(text: object, style: str = "body") -> Paragraph:
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), styles[style])


def bullet(text: str) -> Paragraph:
    return Paragraph(f"• {escape(text)}", ParagraphStyle("bullet", parent=styles["body"], leftIndent=4 * mm, firstLineIndent=-4 * mm))


def table(rows: list[list[object]], widths: list[float], font_size: float = 7.4) -> Table:
    formatted = []
    for row_index, row in enumerate(rows):
        style = "table_head" if row_index == 0 else "table"
        formatted.append([p(item, style) for item in row])
    result = Table(formatted, colWidths=widths, repeatRows=1, hAlign="LEFT")
    result.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#243B64")),
        ("GRID", (0, 0), (-1, -1), 0.35, GRAY_300),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("FONTSIZE", (0, 1), (-1, -1), font_size),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FC")]),
    ]))
    return result


def callout(text: str, background=PALE_GREEN, border=GREEN) -> Table:
    result = Table([[p(text, "callout")]], colWidths=[170 * mm])
    result.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), background),
        ("BOX", (0, 0), (-1, -1), 1, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return result


class Report(BaseDocTemplate):
    def __init__(self, filename: str):
        super().__init__(filename, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=18 * mm)
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="main")
        self.addPageTemplates(PageTemplate(id="all", frames=[frame], onPage=self._footer))

    @staticmethod
    def _footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(FONT, 7)
        canvas.setFillColor(GRAY_500)
        canvas.drawString(20 * mm, 10 * mm, "ABLESTACK TechFlow · Issue #18")
        canvas.drawRightString(190 * mm, 10 * mm, str(doc.page))
        canvas.restoreState()


def build() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    release = data["release"]
    drill = data["drill"]
    final = data["finalState"]
    security = data["security"]
    story = [
        p("ABLESTACK TECHFLOW · ISSUE #18", "meta"), Spacer(1, 10 * mm),
        p("Activepieces 버전·이미지 Digest 고정", "title"), Spacer(1, 4 * mm),
        p("불변 이미지 배포, 반복 재현성과 무빌드 롤백 검증 보고서", "subtitle"), Spacer(1, 18 * mm),
        table([
            ["항목", "내용"],
            ["릴리스", release["releaseId"]],
            ["검증 시각", data["validatedAt"]],
            ["환경", "Ubuntu 24.04 · linux/amd64 · Activepieces 0.86.3"],
            ["검증 범위", "6 Services · Repeat Deploy · Rollback · Volumes · Security"],
            ["상태", data["status"].upper()],
        ], [42 * mm, 128 * mm]), Spacer(1, 8 * mm),
        p("이 문서와 구조화 증적에는 비밀번호, API Key, Cookie, Flow Payload, 사용자 식별자와 원문 운영 로그가 포함되지 않는다.", "small"), PageBreak(),

        p("1. 결과 요약", "h1"),
        callout("여섯 서비스를 검토된 불변 이미지 조합으로 배포하고, 같은 잠금 반복 배포와 직전 Runtime Lock 롤백을 실제 서버에서 검증했다."), Spacer(1, 5 * mm),
        table([
            ["영역", "실증", "판정"],
            ["이미지", "외부 5개 Tag+Digest · Gateway Image ID", "PASS"],
            ["서비스", f'{final["healthyServices"]}/{final["totalServices"]} Compose Health', "PASS"],
            ["반복 배포", "Runtime Image ID 6/6 동일", "PASS"],
            ["롤백", "직전 Runtime Lock · Local-only · No-build", drill["rollbackHealth"]],
            ["상태", f'{drill["persistentVolumeCount"]} Volumes 이름 보존', "PASS"],
            ["외부 경로", f'HTTPS {final["publicHttpsStatus"]}', "PASS"],
            ["관측", "Critical 0 · Warning 0", "PASS"],
            ["보안", f'Secret 누출 {security["secretLeaks"]}', "PASS"],
        ], [36 * mm, 100 * mm, 34 * mm]),
        p("운영 의미", "h2"),
        bullet("mutable Tag가 같은 이름으로 다른 이미지를 배포하는 위험을 차단했다."),
        bullet("배포 전에 상태 백업과 직전 Runtime Lock이 자동 생성된다."),
        bullet("장애 시 Registry나 빌드 환경에 의존하지 않고 로컬 이미지로 복귀한다."), PageBreak(),

        p("2. 이미지 잠금과 책임 경계", "h1"),
        table([
            ["서비스", "버전", "불변 식별", "정책"],
            ["PostgreSQL", "0.8.0-pg14", "Registry Digest", "Pull"],
            ["Redis", "7.0.7", "Registry Digest", "Pull"],
            ["Activepieces App", "0.86.3", "Registry Digest", "Pull"],
            ["Activepieces Worker", "0.86.3", "Registry Digest", "Pull"],
            ["Event Gateway", "0.1.0", "Local Image ID", "No-build"],
            ["Gateway Base", "Python 3.12.11", "Registry Digest", "Build input"],
            ["Caddy", "2.8.4", "Registry Digest", "Pull"],
        ], [41 * mm, 38 * mm, 55 * mm, 36 * mm]),
        p("책임", "h2"),
        bullet("개발자는 릴리스 노트, Schema, 보안 영향과 버전을 검토한다."),
        bullet("운영자는 승인 잠금으로만 배포하고 Health·Observer를 확인한다."),
        bullet("TechFlow 스크립트는 잠금 형식, 소스 일치, 이미지와 런타임 상태를 검증한다."),
        bullet("Activepieces는 Flow 실행 엔진이며 TechFlow의 릴리스 승인과 롤백 정책을 소유하지 않는다."), PageBreak(),

        p("3. 업그레이드·롤백 드릴", "h1"),
        table([
            ["단계", "수행", "결과"],
            ["Baseline", "Runtime Lock · Volume 목록", "Captured"],
            ["Backup", "PostgreSQL Dump · Redis RDB · Manifest", "PASS"],
            ["Locked deploy", "Digest Pull · Gateway ID · No-build", "PASS"],
            ["Repeat", "같은 잠금 재배포 · 6 ID 비교", "IDENTICAL"],
            ["Rollback", "Baseline Lock · Local-only · No-build", drill["rollbackHealth"]],
            ["Final", "목표 릴리스 재배포", drill["finalLockedReleaseHealth"]],
            ["Volumes", "postgres · redis · cache 이름 비교", "UNCHANGED"],
        ], [34 * mm, 100 * mm, 36 * mm]), Spacer(1, 5 * mm),
        callout("반복 배포와 최종 복귀에서 여섯 Runtime Image ID가 동일했고 세 영속 Volume 이름이 유지됐다."),
        p("데이터 호환성", "h2"),
        bullet("Schema downgrade가 불가능한 버전은 이미지 롤백만 수행하지 않는다."),
        bullet("ADR-0003의 격리 복구를 먼저 검증하고 유지보수 창에서 상태와 이미지를 함께 복원한다."), PageBreak(),

        p("4. Gateway 빌드 재현성 판단", "h1"),
        callout("M0의 완료 범위는 같은 승인 이미지를 재현 가능하게 배포·복구하는 것이며, 임의 환경에서 바이트 동일 이미지를 재빌드하는 것까지는 아니다.", background=PALE_AMBER, border=AMBER), Spacer(1, 6 * mm),
        bullet("고정 Base Digest, SOURCE_DATE_EPOCH=0, provenance 비활성화로 no-cache 빌드를 두 번 비교했다."),
        bullet("COPY 계층과 최종 Image ID가 달라 Source-to-image byte reproducibility는 실패로 판정했다."),
        bullet("Gateway를 한 번 빌드해 Image ID를 승인하고 배포·롤백에서는 빌드를 금지했다."),
        bullet("기대 Image ID가 다르면 배포를 시작하기 전에 Fail Closed 한다."),
        p("제품화 Gate", "h2"),
        table([
            ["Gate", "목적"],
            ["Approved Registry Digest", "호스트 간 같은 Artifact 배포"],
            ["SBOM", "구성 요소와 라이선스·취약점 추적"],
            ["Image Signature", "승인 주체와 무결성 확인"],
            ["Provenance/Attestation", "빌드 입력·환경·과정 증명"],
            ["Vulnerability Policy", "차단 등급 취약점의 배포 방지"],
        ], [66 * mm, 104 * mm]), PageBreak(),

        p("5. 통합 검증과 보안", "h1"),
        table([["ID", "검증", "결과"]] + [
            [item["id"], item["name"], item["result"] + (f' ({item["count"]})' if "count" in item else "")]
            for item in data["verification"]
        ], [16 * mm, 119 * mm, 35 * mm], 6.8), Spacer(1, 5 * mm),
        callout("V1–V13 전체 PASS. 런타임 Secret 6종과 릴리스 객체 15개를 대조해 누출 0건을 확인했다."),
        p("보안 판정", "h2"),
        bullet("잠금·드릴 증적에는 이미지 식별자, Health와 시각만 기록한다."),
        bullet("Runtime Lock과 Drill은 root:root 0640으로 제한한다."),
        bullet("Secret, Cookie, Payload, 사용자 정보와 원문 로그는 기록하지 않는다."), PageBreak(),

        p("6. 완료 판정과 다음 단계", "h1"),
        callout("최종 판정: VALIDATED. Issue #18의 같은 구성 재현, 롤백 버전 기록, 운영 문서와 보안 영향 반영 기준을 충족했다."), Spacer(1, 6 * mm),
        table([
            ["완료 자산", "역할"],
            ["ADR-0005", "잠금·승인·롤백·무효화 기준"],
            ["image-lock.json", "여섯 서비스의 단일 릴리스 기준"],
            ["배포·롤백 스크립트", "사전 백업·No-build·Health·Digest 검증"],
            ["Runtime Lock·Drill", "이전·현재·반복·복구 증적"],
            ["Runbook", "준비·배포·롤백·데이터 비호환 처리"],
            ["JSON·PDF·PPTX·Manifest", "일관된 완료 증적"],
        ], [62 * mm, 108 * mm]),
        p("후속 실행", "h2"),
        bullet("Issue #19: GitHub PR Merge Webhook 기반 첫 사내 업무 자동화 Flow"),
        bullet("제품화 Track: Gateway Registry 게시와 SBOM·서명·취약점 Gate"),
        bullet("버전 업그레이드 때마다 Schema·환경 변수·보안 영향과 롤백 드릴을 반복한다."), Spacer(1, 8 * mm),
        p("고객 공개 여부는 제품 책임자의 별도 결정이며 구현 완료 판정을 제한하지 않는다.", "small"),
    ]
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    Report(str(OUTPUT_PATH)).build(story)
    print(OUTPUT_PATH)


if __name__ == "__main__":
    build()
