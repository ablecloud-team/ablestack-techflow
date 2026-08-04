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
OUTPUT = ROOT / "output" / "pdf" / "techflow-ai-gateway-foundation-report.pdf"
FONT = "MalgunGothic"
BOLD = "MalgunGothicBold"
pdfmetrics.registerFont(TTFont(FONT, "C:/Windows/Fonts/malgun.ttf"))
pdfmetrics.registerFont(TTFont(BOLD, "C:/Windows/Fonts/malgunbd.ttf"))

BLACK = colors.HexColor("#111111")
GRAY = colors.HexColor("#5B616B")
LINE = colors.HexColor("#D4D8DF")
BLUE = colors.HexColor("#3D8DFF")
PALE_BLUE = colors.HexColor("#DDF3FF")
GREEN = colors.HexColor("#117A4B")
PALE_GREEN = colors.HexColor("#E8F5EE")
RED = colors.HexColor("#B42318")
PALE_RED = colors.HexColor("#FDE8E7")

base = getSampleStyleSheet()
styles = {
    "meta": ParagraphStyle("meta", parent=base["Normal"], fontName=FONT, fontSize=9, leading=13, textColor=GRAY),
    "title": ParagraphStyle("title", parent=base["Title"], fontName=BOLD, fontSize=26, leading=37, textColor=BLACK),
    "subtitle": ParagraphStyle("subtitle", parent=base["Normal"], fontName=FONT, fontSize=13, leading=20, textColor=GRAY),
    "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName=BOLD, fontSize=19, leading=27, textColor=BLACK, spaceAfter=5 * mm),
    "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName=BOLD, fontSize=12, leading=18, textColor=BLACK, spaceBefore=4 * mm, spaceAfter=2 * mm),
    "body": ParagraphStyle("body", parent=base["BodyText"], fontName=FONT, fontSize=9, leading=14, textColor=colors.HexColor("#30343B"), spaceAfter=2 * mm),
    "small": ParagraphStyle("small", parent=base["BodyText"], fontName=FONT, fontSize=7.2, leading=10.5, textColor=GRAY),
    "callout": ParagraphStyle("callout", parent=base["BodyText"], fontName=BOLD, fontSize=10.5, leading=17, textColor=BLACK),
    "table": ParagraphStyle("table", parent=base["BodyText"], fontName=FONT, fontSize=7.2, leading=10.5, textColor=colors.HexColor("#30343B")),
    "table_head": ParagraphStyle("table_head", parent=base["BodyText"], fontName=BOLD, fontSize=7.2, leading=10.5, textColor=colors.white),
}


def p(value, style="body"):
    return Paragraph(escape(str(value)).replace("\n", "<br/>"), styles[style])


def bullet(value):
    style = ParagraphStyle("bullet", parent=styles["body"], leftIndent=4 * mm, firstLineIndent=-4 * mm)
    return Paragraph(f"• {escape(value)}", style)


def make_table(rows, widths):
    formatted = []
    for index, row in enumerate(rows):
        style = "table_head" if index == 0 else "table"
        formatted.append([p(cell, style) for cell in row])
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


def callout(value, background=PALE_GREEN, border=GREEN):
    result = Table([[p(value, "callout")]], colWidths=[170 * mm])
    result.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), background), ("BOX", (0, 0), (-1, -1), 1, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return result


class Report(BaseDocTemplate):
    def __init__(self, filename):
        super().__init__(filename, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=18 * mm)
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="main")
        self.addPageTemplates(PageTemplate(id="all", frames=[frame], onPage=self.footer))

    @staticmethod
    def footer(canvas, doc):
        canvas.setTitle("TechFlow Issue #41 AI Gateway 기반 구현 완료 보고서")
        canvas.setAuthor("ABLESTACK TechFlow")
        canvas.saveState()
        canvas.setFont(FONT, 7)
        canvas.setFillColor(GRAY)
        canvas.drawString(20 * mm, 10 * mm, "ABLESTACK TechFlow · Issue #41 · AI Gateway Foundation")
        canvas.drawRightString(190 * mm, 10 * mm, str(doc.page))
        canvas.restoreState()


story = [
    p("ABLESTACK TECHFLOW · ISSUE #41 · IMPLEMENTED", "meta"), Spacer(1, 10 * mm),
    p("AI Gateway API·DB·Mock Provider 기반 구현 완료", "title"), Spacer(1, 4 * mm),
    p("11개 API · 15개 RAG Table · 3개 Provider Profile · 테스트 서버 배포", "subtitle"), Spacer(1, 16 * mm),
    make_table([
        ["항목", "결과"], ["서비스", "techflow-ai-gateway 0.1.0"], ["API", "11 Operations"],
        ["Database", "PostgreSQL 14 · pgvector · 15 Tables"], ["Provider", "3 Profiles · Deterministic Mock"],
        ["실서버", "Gateway·Database Healthy · Canary PASS"], ["판정", "Issue #41 완료 · 다음 #42"],
    ], [48 * mm, 122 * mm]), Spacer(1, 8 * mm),
    p("실제 Secret, Source 원문, Prompt·응답 원문과 인증정보는 포함하지 않는다.", "small"), PageBreak(),

    p("1. 완료 범위와 경계", "h1"),
    callout("API·DB·Provider 계약을 실제 실행 가능한 코드로 고정했다. Source Fetch와 OpenAI 호출은 후속 이슈 승인 전까지 비활성 상태다."), Spacer(1, 5 * mm),
    make_table([
        ["구성요소", "#41 책임", "후속"],
        ["Activepieces", "변경 감지·승인·재색인 Flow", "#45"],
        ["AI Gateway", "API·상태·정책·멱등성·검증", "#42~#44"],
        ["PostgreSQL", "Source·작업·Chunk·평가·감사", "#42~#46"],
        ["Mock Provider", "Responses·Embedding 계약 검증", "#43·#44에서 실제 Adapter"],
    ], [38 * mm, 75 * mm, 57 * mm]),
    p("안전한 미구현 상태", "h2"), bullet("RAG 질의는 ABSTAINED와 providerCalled=false를 반환한다."), bullet("실제 OpenAI Key와 GitHub Token은 Compose·문서·Issue에 저장하지 않는다."), PageBreak(),

    p("2. 11개 API 계약", "h1"),
    make_table([
        ["분류", "Operation", "통제"],
        ["Health", "GET /healthz", "DB·Vector 준비 상태"],
        ["Source", "Create · Get · Approve · Delete", "승인 Commit · 철회"],
        ["Compatibility", "Create Set", "승인 Source만 조합"],
        ["Ingestion", "Create Ingestion · Get Job", "202 Job · 멱등성"],
        ["RAG", "Query", "ABSTAINED · Provider 0"],
        ["Evaluation", "Create Run · Get Run", "평가 상태·결과"],
    ], [34 * mm, 74 * mm, 62 * mm]), Spacer(1, 5 * mm),
    callout("모든 /v1 요청은 X-Correlation-Id를, 상태 변경 요청은 Idempotency-Key를 요구한다.", PALE_BLUE, BLUE),
    p("오류 처리", "h2"), bullet("Validation 오류는 입력 질문·Chunk·Secret을 다시 출력하지 않는다."), bullet("로그는 Route·Status·Latency·Correlation·Error Type만 기록한다."), PageBreak(),

    p("3. 15개 테이블과 최소권한", "h1"),
    make_table([
        ["그룹", "테이블", "핵심 통제"],
        ["Source", "source · source_version", "Commit pin · D0"],
        ["Compatibility", "set · set_source", "승인 조합"],
        ["Ingestion", "job · chunk", "멱등성·상태"],
        ["Embedding", "profile · chunk_embedding", "vector(3072)"],
        ["Code", "symbol · relation", "Path·Lineage"],
        ["Deletion", "deletion_ledger", "철회·삭제 추적"],
        ["Evaluation", "case · run · result", "Golden Run"],
        ["Provider", "provider_call", "안전 메타데이터"],
    ], [38 * mm, 72 * mm, 60 * mm]),
    p("Role", "h2"), bullet("migrator, app, source_fetcher 세 NOLOGIN Group Role을 분리한다."), bullet("App Schema Create=false, Fetcher Provider Audit Select=false를 실서버에서 확인했다."), PageBreak(),

    p("4. Provider Profile과 Mock Adapter", "h1"),
    make_table([
        ["Profile", "계약", "#41 실행"],
        ["OPENAI_RAG_DEFAULT_V1", "gpt-5.6-terra · medium", "Mock Structured Output"],
        ["OPENAI_RAG_ESCALATION_V1", "gpt-5.6-sol · high", "Mock Structured Output"],
        ["OPENAI_EMBEDDING_V1", "text-embedding-3-large · 3,072", "Mock Deterministic Vector"],
    ], [62 * mm, 58 * mm, 50 * mm]), Spacer(1, 6 * mm),
    callout("실제 호출을 하기 전에 Profile, 구조화 출력, Vector 차원, D0 Chunk와 요청 크기 계약을 자동 테스트한다."),
    p("Provider Guard", "h2"), bullet("store=false, background=false, Tool 0, 최대 D0 Chunk 10개"), bullet("등록되지 않은 Profile, D1~D3, Tool·Store 요청은 호출 전에 차단"), bullet("Provider 감사에는 원문 Prompt·Response·Credential을 저장하지 않음"), PageBreak(),

    p("5. 컨테이너·네트워크·Secret", "h1"),
    make_table([
        ["통제", "구현", "실서버"],
        ["Runtime User", "10001:10001", "확인"],
        ["Root FS", "Read-only", "true"],
        ["Capabilities", "Drop ALL", "[ALL]"],
        ["DB Network", "rag_internal", "Host Port 0"],
        ["Gateway Bind", "127.0.0.1:18090", "8090/tcp"],
        ["Base Images", "Digest pin", "Python·pgvector"],
        ["Secrets", "Operator file mount", "Repository 값 0"],
    ], [42 * mm, 72 * mm, 56 * mm]), Spacer(1, 5 * mm),
    callout("AI Gateway Compose Project는 기존 Activepieces Stack·Volume·Database와 분리했다.", PALE_BLUE, BLUE), PageBreak(),

    p("6. 자동 검증 결과", "h1"),
    make_table([
        ["검증", "기대", "결과"],
        ["Service Tests", "API·Config·Store·Provider·Migration·Container", "58/58 PASS"],
        ["Repository Validator", "API 11 · Table 15 · Profile 3 · Secret 0", "3/3 PASS"],
        ["OpenAPI", "정확히 11 Operations", "PASS"],
        ["SQL", "4 Migration parse", "PASS"],
        ["Database", "15 Tables · 2 Extensions · 최소권한", "PASS"],
        ["Runtime Canary", "전체 API Lifecycle", "PASS"],
        ["Query", "ABSTAINED · Provider false", "PASS"],
    ], [50 * mm, 80 * mm, 40 * mm]), Spacer(1, 6 * mm),
    callout("정적 검증과 실제 PostgreSQL·Container Canary가 같은 계약을 확인했다."), PageBreak(),

    p("7. 테스트 서버 배포 증적", "h1"),
    make_table([
        ["항목", "확인값"],
        ["Compose Project", "techflow-ai-gateway"],
        ["Gateway", "healthy · 127.0.0.1:18090→8090"],
        ["Database", "healthy · internal only"],
        ["Image ID", "sha256:99ef2675b928…39cb2fe3bfb"],
        ["Schema", "15 Tables · vector + pg_trgm"],
        ["Canary Final", "Source WITHDRAWN · Query ABSTAINED"],
        ["Provider", "providerCalled=false"],
    ], [48 * mm, 122 * mm]), Spacer(1, 6 * mm),
    p("검증 순서", "h2"), bullet("Source 생성 → 승인 → Ingestion → Compatibility → Query → Evaluation → 철회"), bullet("Migration Verify → DB Role 권한 → Container User·Read-only·Port 확인"), PageBreak(),

    p("8. 배포 중 발견한 문제와 개선", "h1"),
    make_table([
        ["발견", "원인", "개선"],
        ["Init SQL Permission", "Archive 권한 과도 제한", "SQL 644 · Script 755"],
        ["Login Auth 실패", "Secret File 600", "상위 700 · File 644"],
        ["Host Port 미게시", "Internal Network only", "Gateway Edge Network 분리"],
        ["API Job 500", "job_id 매핑 오류", "Adapter 수정 · 회귀 테스트 2"],
    ], [48 * mm, 58 * mm, 64 * mm]), Spacer(1, 6 * mm),
    callout("각 문제를 Runbook에 원인·판정·복구 절차로 자산화했고 기존 Activepieces 자산은 변경하지 않았다.", PALE_GREEN, GREEN),
    p("롤백", "h2"), bullet("Ingress 차단 → 상태 Backup → 직전 Image → 필요 시 Down Migration"), bullet("Schema Verify → DB 권한 → Runtime Canary 순서로 복구 판정"), PageBreak(),

    p("9. 완료 판정과 다음 단계", "h1"),
    callout("Issue #41은 구현·테스트·실서버 배포·검증·롤백 문서화 기준을 충족했다."), Spacer(1, 6 * mm),
    make_table([
        ["순서", "Issue", "목표"],
        ["완료", "#41", "AI Gateway API·DB·Mock Provider 기반"],
        ["다음", "#42", "9개 Source Profile 승인·수집"],
        ["후속", "#43", "문서·코드 Retrieval·Embeddings"],
        ["후속", "#44", "Responses·Routing·Citation 검증"],
        ["후속", "#45·#46", "Activepieces 연동·품질·보안·E2E"],
    ], [30 * mm, 30 * mm, 110 * mm]),
    p("다음 Gate", "h2"), bullet("#42 승인 전 실제 Source Fetch를 시작하지 않는다."), bullet("#43·#44 승인 전 OpenAI Credential을 주입하거나 실제 호출하지 않는다."),
    Spacer(1, 10 * mm), p("ABLESTACK TechFlow · Issue #41 Complete · 2026-08-04", "small"),
]

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
Report(str(OUTPUT)).build(story)
print(OUTPUT)
