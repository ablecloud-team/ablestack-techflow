#!/usr/bin/env python3
"""Build the Issue #43 implementation and validation report."""

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
OUTPUT = ROOT / "output/pdf/techflow-parser-embedding-report.pdf"
FONT, BOLD = "MalgunGothic", "MalgunGothicBold"
pdfmetrics.registerFont(TTFont(FONT, "C:/Windows/Fonts/malgun.ttf"))
pdfmetrics.registerFont(TTFont(BOLD, "C:/Windows/Fonts/malgunbd.ttf"))

BLACK = colors.HexColor("#101010")
GRAY = colors.HexColor("#5B616B")
LINE = colors.HexColor("#D4D8DF")
BLUE = colors.HexColor("#3D8DFF")
PALE = colors.HexColor("#DDF3FF")
GREEN = colors.HexColor("#117A4B")
RED = colors.HexColor("#C42B1C")

base = getSampleStyleSheet()
styles = {
    "meta": ParagraphStyle("meta", parent=base["Normal"], fontName=FONT, fontSize=8.5, leading=12, textColor=GRAY),
    "title": ParagraphStyle("title", parent=base["Title"], fontName=BOLD, fontSize=24, leading=34, textColor=BLACK),
    "subtitle": ParagraphStyle("subtitle", parent=base["Normal"], fontName=FONT, fontSize=11, leading=18, textColor=GRAY),
    "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName=BOLD, fontSize=17, leading=25, textColor=BLACK, spaceAfter=4 * mm),
    "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName=BOLD, fontSize=11, leading=17, textColor=BLACK, spaceBefore=2 * mm, spaceAfter=2 * mm),
    "body": ParagraphStyle("body", parent=base["BodyText"], fontName=FONT, fontSize=9, leading=14, textColor=colors.HexColor("#30343B"), spaceAfter=2 * mm),
    "small": ParagraphStyle("small", parent=base["BodyText"], fontName=FONT, fontSize=7.4, leading=10.5, textColor=GRAY),
    "callout": ParagraphStyle("callout", parent=base["BodyText"], fontName=BOLD, fontSize=10.5, leading=17, textColor=BLACK),
    "table": ParagraphStyle("table", parent=base["BodyText"], fontName=FONT, fontSize=7.4, leading=10.5, textColor=colors.HexColor("#30343B")),
    "table_head": ParagraphStyle("table_head", parent=base["BodyText"], fontName=BOLD, fontSize=7.4, leading=10.5, textColor=colors.white),
}


def p(value, style="body"):
    return Paragraph(escape(str(value)).replace("\n", "<br/>"), styles[style])


def bullet(value):
    style = ParagraphStyle("bullet", parent=styles["body"], leftIndent=5 * mm, firstLineIndent=-4 * mm)
    return Paragraph(f"- {escape(value)}", style)


def table(rows, widths):
    formatted = [[p(cell, "table_head" if row_index == 0 else "table") for cell in row]
                 for row_index, row in enumerate(rows)]
    result = Table(formatted, colWidths=widths, repeatRows=1, hAlign="LEFT")
    result.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#243B64")),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FC")]),
    ]))
    return result


def callout(text, color=BLUE):
    item = Table([[p(text, "callout")]], colWidths=[174 * mm])
    item.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE), ("BOX", (0, 0), (-1, -1), 1.2, color),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return item


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(FONT, 7)
    canvas.setFillColor(GRAY)
    canvas.drawString(18 * mm, 10 * mm, "ABLESTACK TechFlow · Issue #43")
    canvas.drawRightString(192 * mm, 10 * mm, f"{doc.page:02d}")
    canvas.restoreState()


OUTPUT.parent.mkdir(parents=True, exist_ok=True)
doc = BaseDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
                      topMargin=16 * mm, bottomMargin=17 * mm,
                      title="TechFlow Issue #43 Parser·Embedding·검색 구현 완료 보고서",
                      author="ABLESTACK TechFlow")
doc.addPageTemplates([PageTemplate(id="normal", frames=[Frame(doc.leftMargin, doc.bottomMargin,
    doc.width, doc.height, id="content")], onPage=footer)])

story = []
story += [Spacer(1, 17 * mm), p("ABLESTACK TECHFLOW · ISSUE #43", "meta"), Spacer(1, 9 * mm),
          p("Parser·Chunk·Embedding·검색\n구현 및 서버 실증 완료", "title"), Spacer(1, 6 * mm),
          p("승인된 ABLESTACK 소스를 실행하지 않고 검색 가능한 근거로 전환하는 AI Gateway 0.3.0 구현 보고서", "subtitle"),
          Spacer(1, 18 * mm), callout("34 Files · 64 Chunks · 64 Embeddings · 10 Source-pinned Results"),
          Spacer(1, 8 * mm), p("GENIE_MASTER · master@3e3c5c364f5c7261b07d49fcbcd4f3605b91f3b1", "meta"),
          p("시험 서버 · Mock Embedding · 외부 OpenAI 호출 0 · 2026-08-05", "meta"), PageBreak()]

story += [p("1. 완료 판정", "h1"),
          p("Issue #43의 구현, 시험 서버 배포, 승인 GENIE Canary, 검색, 재시작 영속성, 격리 삭제 Drill, 문서와 PDF/PPTX 자산화를 완료했습니다."),
          table([["영역", "결과", "판정"], ["Gateway", "0.3.0 · Healthy", "PASS"],
                 ["Source", "GENIE 34 / 34", "PASS"], ["Index", "64 Chunk · 64 Embedding", "PASS"],
                 ["Search", "Top 10 · Commit/Path/Line", "PASS"], ["Delete", "64/64/15/45 · 잔여 0", "PASS"],
                 ["Tests", "87 passed · 4 subtests", "PASS"]], [35 * mm, 104 * mm, 35 * mm]),
          Spacer(1, 6 * mm), callout("검색 근거 계층은 완료됐으며 답변 생성은 Issue #44까지 명시적으로 보류합니다.", GREEN),
          Spacer(1, 6 * mm), p("검토자가 확인할 핵심", "h2"),
          bullet("Source Version과 인용 Commit이 동일한가"), bullet("34개 Eligible File 전체가 성공한 후에만 활성화됐는가"),
          bullet("실 Provider 호출 없이도 OpenAI Adapter 계약과 Secret 경계가 검증됐는가"),
          bullet("철회 시 검색 제외와 파생 데이터 삭제가 재현 가능한가"), PageBreak()]

story += [p("2. 처리 아키텍처", "h1"),
          table([["단계", "입력", "출력", "안전 경계"],
                 ["Parse", "검증된 UTF-8 Blob", "Chunk·Symbol·Relation", "실행·Import·Build·Test 0"],
                 ["Embed", "최대 24 KiB Chunk", "3072차원 Vector", "Runtime Secret File 전용"],
                 ["Retrieve", "질문+Source Scope", "상위 10개 근거", "ACTIVE·D0 Scope 선적용"],
                 ["Generate", "검색 근거", "미구현", "Issue #44까지 ABSTAINED"]],
                [28 * mm, 50 * mm, 48 * mm, 48 * mm]),
          Spacer(1, 5 * mm), p("OpenAI 연계", "h2"),
          bullet("공식 OpenAI Python SDK 2.53.0과 Embeddings API Adapter를 사용합니다."),
          bullet("Model은 text-embedding-3-large, Dimension은 3072로 Profile에 고정합니다."),
          bullet("원본 Repository를 OpenAI File 또는 Vector Store에 업로드하지 않습니다."),
          bullet("감사에는 Provider·Model·Request ID·Token·Latency만 남기고 원문·Secret을 저장하지 않습니다."),
          Spacer(1, 5 * mm), callout("이번 Canary는 Mock Provider입니다. 실 OpenAI Canary는 운영 API Key를 보호 파일로 주입한 뒤 동일 Adapter 경로에서 별도 수행합니다."),
          Spacer(1, 5 * mm), p("공식 참고", "h2"),
          p("https://developers.openai.com/api/reference/resources/embeddings/methods/create", "small"),
          p("https://developers.openai.com/api/docs/models/text-embedding-3-large", "small"), PageBreak()]

story += [p("3. Parser·Chunk·Embedding 계약", "h1"),
          table([["계약", "설정", "서버 결과"],
                 ["Parser", "TREE_SITTER_V1 · Parser 13종", "8 Parsed · 26 Fallback"],
                 ["Fallback", "최대 160 Line · Overlap 20", "결정론적 분할"],
                 ["Chunk", "최대 24 KiB · UUIDv5", "64개"],
                 ["Symbol", "Package·Name·Signature·Line", "15개"],
                 ["Relation", "Import·Inheritance·Declaration·Reference", "45개"],
                 ["Embedding", "OPENAI_EMBEDDING_V1 · 3072", "64개 · Batch 1"]],
                [38 * mm, 91 * mm, 45 * mm]),
          Spacer(1, 5 * mm), p("Hybrid Retrieval", "h2"),
          bullet("후보 전에 Source Profile 또는 Compatibility Set, D0, ACTIVE를 필터합니다."),
          bullet("FTS 20, Identifier 20, exact cosine 30 후보를 생성합니다."),
          bullet("RRF k=60으로 결합하고 TEST_CODE Weight 0.6을 적용합니다."),
          bullet("최대 10개 Repository·Branch·Commit·Path·Line·Symbol 인용을 반환합니다."),
          Spacer(1, 5 * mm), callout("현재 활성 Chunk 64개에서는 exact cosine이 가장 단순하고 재현성이 높습니다. HNSW는 50,000 Chunk Gate에서 재검토합니다.", GREEN), PageBreak()]

story += [p("4. 시험 서버 실증", "h1"),
          table([["항목", "실측"], ["Source", "GENIE_MASTER · 34 / 34"],
                 ["Commit", "3e3c5c364f5c7261b07d49fcbcd4f3605b91f3b1"],
                 ["Index", "64 Chunk · 64 Embedding · 15 Symbol · 45 Relation"],
                 ["Gateway", "0.3.0 · Healthy · pgvector ready"],
                 ["Runtime", "UID 10001 · Read-only Root FS"],
                 ["Disk", "1,005 GiB · 950 GiB available · 2% used"],
                 ["Isolation", "Activepieces 6 Container all healthy"]], [42 * mm, 132 * mm]),
          Spacer(1, 5 * mm), p("인용 예시", "h2"),
          p("ablecloud-team/ablestack-genie / master / 3e3c5c... / genie-shell/README.md / lines 28-34"),
          p("상위 결과는 Automation Controller와 AWX 개발환경 구성 절차를 승인 Commit의 Line Range로 반환했습니다."),
          Spacer(1, 5 * mm), p("재시작 영속성", "h2"),
          bullet("Gateway 재시작 후 Health 200과 Version 0.3.0을 확인했습니다."),
          bullet("재시작 후에도 Source ACTIVE, 34 / 34, Chunk·Embedding 64 / 64를 유지했습니다."),
          bullet("OpenAI Key 환경변수 0건, Provider Audit은 Mock Embeddings 1건만 기록됐습니다."), PageBreak()]

story += [p("5. 실패 보상과 삭제 Drill", "h1"),
          p("최초 서버 실행에서 DB Row Alias와 JSONB Adapter 결함을 발견했습니다. 두 실패 모두 Source를 APPROVED로 복귀시키고 활성 Chunk 0건을 유지했습니다. 수정 후 새 Job과 새 멱등키로 34 / 34 활성화에 성공했습니다."),
          table([["상황", "보상", "검증"], ["Parsing·DB 실패", "Job FAILED", "부분 활성화 0"],
                 ["Source 상태", "APPROVED 복귀", "재검토·재실행 가능"],
                 ["재실행", "새 Job·새 멱등키", "SUCCEEDED"],
                 ["활성 전환", "전체 파일 일치 후 원자 전환", "34 = 34"]], [45 * mm, 74 * mm, 55 * mm]),
          Spacer(1, 6 * mm), p("격리 삭제 Drill", "h2"),
          table([["파생 데이터", "삭제", "잔여"], ["Chunk", "64", "0"], ["Embedding", "64", "0"],
                 ["Symbol", "15", "0"], ["Relation", "45", "0"]], [60 * mm, 55 * mm, 55 * mm]),
          Spacer(1, 5 * mm), callout("Live GENIE Index는 유지하고 임시 DB techflow_rag_issue43_drill에서 검증한 뒤 정확한 임시 DB만 제거했습니다.", GREEN), PageBreak()]

story += [p("6. 배포·백업·롤백", "h1"),
          table([["자산", "경로·값"], ["배포", "/home/ablecloud/techflow-ai-gateway"],
                 ["Release", "issue-43"], ["Image", "sha256:d767e54b...fdd3e"],
                 ["Backup", "backups/issue43-20260805T1444KST"],
                 ["DB", "techflow-rag.dump"], ["Code", "pre-deploy-code.tgz"],
                 ["Integrity", "checksums.sha256"]], [42 * mm, 132 * mm]),
          Spacer(1, 5 * mm), p("배포 절차", "h2"),
          bullet("Compose Rendering과 Digest 고정을 확인합니다."),
          bullet("Tree-sitter Parser 13종을 Image Build 시 Prefetch합니다."),
          bullet("0005 Migration 적용 후 Table 19개와 Issue #43 Column 8개를 검증합니다."),
          bullet("Gateway와 Reconciler만 갱신하고 Activepieces Volume은 변경하지 않습니다."),
          Spacer(1, 5 * mm), p("롤백", "h2"),
          bullet("애플리케이션 오류는 백업된 이전 Image ID로 Gateway를 전환합니다."),
          bullet("Schema 롤백은 DB 백업과 제품 책임자 승인 후 0005 down Migration을 적용합니다."),
          bullet("복원은 새 DB에서 먼저 검증하고 Activepieces와 분리해 전환합니다."), PageBreak()]

story += [p("7. 다음 승인 지점", "h1"),
          p("Issue #43은 검색 근거를 준비했습니다. 다음 Issue #44에서는 이 근거만 사용해 답변 생성과 보류 판정을 구현합니다."),
          table([["순서", "Issue #44 범위"], ["1", "OpenAI Responses Adapter"],
                 ["2", "Structured Output과 Citation 사용 검증"],
                 ["3", "근거 부족·충돌·Test-only ABSTAINED 판정"],
                 ["4", "Terra 기본·Sol 제한 승격 Routing"],
                 ["5", "운영 API Key 기반 실 Embedding Canary"]], [25 * mm, 149 * mm]),
          Spacer(1, 7 * mm), callout("권장 결정: Issue #43 PR을 검토·병합한 뒤, 운영 API Key를 보호 Secret으로 주입해 실 Embedding Canary를 먼저 증적하고 Issue #44 구현에 착수합니다.", GREEN),
          Spacer(1, 7 * mm), p("관리 자산", "h2"),
          bullet("docs/reports/issue-43-parser-embedding-validation.md"),
          bullet("docs/runbooks/parser-embedding-retrieval.md"),
          bullet("docs/decisions/techflow-parser-embedding-retrieval.json"),
          bullet("output/issue-43-artifact-manifest.json"),
          Spacer(1, 7 * mm), p("판정: IMPLEMENTED · DEPLOYED · VALIDATED", "callout")]

doc.build(story)
print(OUTPUT)
