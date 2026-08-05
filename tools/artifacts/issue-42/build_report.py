#!/usr/bin/env python3
"""Build the Issue #42 persistent-source implementation report PDF."""

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
OUTPUT = ROOT / "output/pdf/techflow-source-registry-report.pdf"
FONT, BOLD = "MalgunGothic", "MalgunGothicBold"
pdfmetrics.registerFont(TTFont(FONT, "C:/Windows/Fonts/malgun.ttf"))
pdfmetrics.registerFont(TTFont(BOLD, "C:/Windows/Fonts/malgunbd.ttf"))

BLACK = colors.HexColor("#101010")
GRAY = colors.HexColor("#5B616B")
LINE = colors.HexColor("#D4D8DF")
BLUE = colors.HexColor("#3D8DFF")
PALE = colors.HexColor("#DDF3FF")
GREEN = colors.HexColor("#117A4B")
PALE_GREEN = colors.HexColor("#E8F5EE")

base = getSampleStyleSheet()
styles = {
    "meta": ParagraphStyle("meta", parent=base["Normal"], fontName=FONT, fontSize=9, leading=13, textColor=GRAY),
    "title": ParagraphStyle("title", parent=base["Title"], fontName=BOLD, fontSize=25, leading=36, textColor=BLACK),
    "subtitle": ParagraphStyle("subtitle", parent=base["Normal"], fontName=FONT, fontSize=12, leading=19, textColor=GRAY),
    "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName=BOLD, fontSize=18, leading=26, textColor=BLACK, spaceAfter=5 * mm),
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


def table(rows, widths):
    formatted = [[p(cell, "table_head" if index == 0 else "table") for cell in row] for index, row in enumerate(rows)]
    result = Table(formatted, colWidths=widths, repeatRows=1, hAlign="LEFT")
    result.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#243B64")),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
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


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(FONT, 7)
    canvas.setFillColor(GRAY)
    canvas.drawString(20 * mm, 12 * mm, "ABLESTACK TechFlow · Issue #42")
    canvas.drawRightString(190 * mm, 12 * mm, str(doc.page))
    canvas.restoreState()


def add_page(story, title, body, last=False):
    story.extend([p(title, "h1"), *body])
    if not last:
        story.append(PageBreak())


story = [
    Spacer(1, 20 * mm), p("ABLESTACK TECHFLOW · ISSUE #42", "meta"), Spacer(1, 10 * mm),
    p("Source Registry·영속 미러·검역\n보완 구현 완료", "title"), Spacer(1, 8 * mm),
    p("7개 Persistent Mirror · 9개 Source Profile · Reviewer dhslove", "subtitle"), Spacer(1, 14 * mm),
    callout("판정: 보완 구현·1TB Root 확장·시험 서버 배포·검증 완료. 실제 Source 승인과 OpenAI 호출은 0건이다.", PALE, BLUE),
    Spacer(1, 14 * mm),
    table([["기준", "결과"], ["Gateway", "0.2.1 / 19 API"], ["Database", "19 Table / 9 Profile / 7 Mirror"], ["Sync", "6시간 / 24시간 Stale"], ["Root", "1,005 GiB / 가용 950 GiB"], ["승인·Provider", "0 / 0"]], [45 * mm, 125 * mm]),
    Spacer(1, 10 * mm), p("검증일 2026-08-05 · 초기 Source Reviewer dhslove", "meta"), PageBreak(),
]

add_page(story, "1. 보완 결론", [
    p("Repository 자료는 질의 때 온라인으로 참조하지 않는다. 발견 단계만 GitHub HTTPS를 사용하고, 7개 저장소를 시험 서버의 영속 Bare Mirror로 유지한다."),
    table([["결정", "구현 결과"], ["저장", "Docker Named Volume에 7개 Bare Mirror 영속"], ["갱신", "Source Reconciler가 시작 시와 21,600초마다 9개 Profile 동기화"], ["검역", "보호 Candidate Commit을 로컬에서만 Tree·Blob Read"], ["질의", "#43 이후 PostgreSQL 승인 Index 사용, GitHub 실시간 의존 없음"], ["장애", "신규 Head만 지연; 기존 Mirror·Blob·Index 유지"]], [38 * mm, 132 * mm]),
    Spacer(1, 7 * mm), callout("현재 실제 정책은 SCHEDULE_6H_RECONCILIATION이다. Push 즉시 갱신은 #45에서 구현한다.", PALE, BLUE),
])

add_page(story, "2. 영속 Source 데이터 경로", [
    table([["단계", "입력 → 출력", "저장·안전 경계"], ["Discovery", "GitHub Branch → Head Commit", "허용 Branch만 증분 Fetch"], ["Mirror", "Head → Candidate Ref", "저장소별 Bare Repo·File Lock"], ["Scan", "Candidate Ref → File Decision", "네트워크 없음·실행 없음"], ["Blob", "D0 적격 Text → rag_source_blob", "Repository+Blob SHA·Content Hash"], ["Index #43", "승인 Blob → Chunk·Embedding", "질의 시 GitHub 불필요"]], [35 * mm, 55 * mm, 80 * mm]),
    Spacer(1, 6 * mm),
    bullet("Cloud main·ablestack-diplo·ablestack-europa는 한 Mirror에서 Profile별 Ref로 분리한다."),
    bullet("Fetch 후 git fsck --connectivity-only와 git gc --auto를 실행한다."),
    bullet("WITHDRAWN Ref 정리는 #43 삭제 전파와 7일 SLA로 구현한다."),
    bullet("Mirror 상태 API는 최근 성공, Commit, 오류, 연속 실패, 지연을 반환한다."),
])

profiles = [["Profile", "Repository", "Branch"],
    ["SHARED_DOCS", "ablestack-docs", "master"], ["CLOUD_MAIN", "ablestack-cloud", "main"],
    ["CLOUD_DIPLO", "ablestack-cloud", "ablestack-diplo"], ["CLOUD_EUROPA", "ablestack-cloud", "ablestack-europa"],
    ["WALL_MAIN", "ablestack-wall", "main"], ["COCKPIT_DIPLO", "ablestack-cockpit-plugin", "ablestack-diplo"],
    ["GENIE_MASTER", "ablestack-genie", "master"], ["KICKSTART_MASTER", "ablestack-kickstart", "master"],
    ["QEMU_EXEC_TOOLS_MAIN", "ablestack-qemu-exec-tools", "main"]]
add_page(story, "3. Source Registry 기준선", [
    p("9개 Profile은 코드와 DB Allowlist로 고정한다. 모든 Profile은 D0, 7일 삭제 SLA, 초기 Reviewer dhslove다."),
    table(profiles, [48 * mm, 72 * mm, 50 * mm]),
    Spacer(1, 5 * mm), p("관찰 Head는 승인 Commit이 아니다. Head 변경은 새 Version을 만들며 기존 승인을 승계하지 않는다.", "small"),
])

add_page(story, "4. 동기화·GitHub 장애 정책", [
    table([["상태", "판정", "운영 동작"], ["HEALTHY", "최근 동기화 성공", "정상 검역·색인 준비"], ["DEGRADED", "최근 Fetch 실패", "기존 Mirror 유지, 신규 Head 보류"], ["STALE", "성공 후 86,400초 초과", "운영 경보, 기존 Index 계속 제공"], ["UNINITIALIZED", "동기화 성공 이력 없음", "승인·색인 금지"]], [35 * mm, 55 * mm, 80 * mm]),
    Spacer(1, 7 * mm),
    bullet("동일 6시간 Window의 Idempotency Key는 중복 Version을 만들지 않는다."),
    bullet("Reconciler 최초 실행은 9개 Profile 모두 성공했다."),
    bullet("GitHub 장애 중에도 기존 보호 Commit 스캔은 가능하다."),
    bullet("Push Webhook 빠른 경로는 #45의 Activepieces 인증 Flow에서 구현한다."),
    Spacer(1, 7 * mm), callout("가용성 경계: GitHub 장애는 Freshness를 낮추지만 현재 승인 지식의 제공을 중단시키지 않는다."),
])

add_page(story, "5. 검역·승인·원자 활성화", [
    table([["영역", "허용", "차단"], ["Git", "HTTPS Fetch, Bare, ls-tree, cat-file", "Checkout, Hook, Submodule, File/Ext"], ["파일", "D0 Text, UTF-8, ≤1 MiB", "Binary, NUL, 생성물, Minified"], ["정보", "Path·Hash·Decision·Rule", "Secret, PII, Credential URL"], ["실행", "정적 Read", "Build, Test, Source 실행"], ["승인", "dhslove + expectedCommit", "승계, 부분 색인, 무승인 활성화"]], [30 * mm, 68 * mm, 72 * mm]),
    Spacer(1, 6 * mm),
    p("REGISTERED → QUARANTINED → APPROVED → INDEXING → ACTIVE 순서를 지키며, 색인 실패는 APPROVED로 복귀한다. Eligible 전 파일 성공 후에만 기존 ACTIVE를 교체한다."),
    callout("실제 Source 승인 0건 · ACTIVE 0건 · OpenAI Provider Call 0건", PALE, BLUE),
])

add_page(story, "6. 자동·오프라인 검증", [
    table([["검증", "결과"], ["Unit·Contract·Store", "73 / 73 통과"], ["OpenAPI / DB", "19 Operation / 19 Table"], ["Registry / Mirror", "9 Profile / 7 Repository"], ["Reconciler", "9 / 9 성공 · 7 HEALTHY"], ["Persistence", "Gateway 재시작 후 7 Mirror 유지"], ["Offline Scan", "network none · GENIE 34 Eligible"], ["Fail closed", "Ingestion 409 · Query ABSTAINED"], ["Activepieces", "기존 6 Container Healthy"]], [52 * mm, 118 * mm]),
    Spacer(1, 6 * mm),
    p("Mirror 총 크기는 906 MiB다. 네트워크가 없는 별도 Container가 보호된 GENIE Commit을 읽어 Candidate 34, Eligible 34, Excluded 0, Blocking 0을 재현했다."),
    callout("오프라인 스캔 성공은 검역 경로가 GitHub에 의존하지 않음을 실제로 입증한다."),
])

add_page(story, "7. 시험 서버 Root 1TB 확장", [
    p("가상 디스크는 1,024 GiB로 확장됐지만 Root PV와 LV는 46.9 GiB였다. Partition Table·VG Metadata를 백업한 뒤 온라인 확장했다."),
    table([["항목", "확장 전", "확장 후"], ["/dev/sda", "1,024 GiB", "1,024 GiB"], ["/dev/sda3", "46.9 GiB", "1,020.9 GiB"], ["ubuntu-lv", "46.9 GiB", "1,020.9 GiB"], ["Root ext4", "45.9 GiB", "1,005 GiB"], ["가용", "약 30 GiB", "950 GiB"], ["사용률", "30%", "2%"]], [62 * mm, 54 * mm, 54 * mm]),
    Spacer(1, 6 * mm),
    bullet("growpart /dev/sda 3 → pvresize /dev/sda3 → lvextend -r 순으로 수행했다."),
    bullet("sgdisk -v는 GPT 오류가 없음을 확인했다."),
    bullet("확장 후 Gateway·Reconciler·Activepieces Health와 Mirror 데이터를 재검증했다."),
    Spacer(1, 6 * mm), callout("Root ext4 1,005 GiB · 사용 14 GiB · 가용 950 GiB · 사용률 2%", PALE, BLUE),
])

add_page(story, "8. 배포·백업·롤백", [
    table([["항목", "증적"], ["배포", "/home/ablecloud/techflow-ai-gateway"], ["Gateway", "0.2.1 · Image 36ee3c…b1b1c · Healthy"], ["DB", "19 Table · 9 Profile · 7 Mirror State"], ["Mirror", "7 Bare Repo · 906 MiB · Named Volume"], ["Backup", "issue42-mirror-20260805T0327KST"], ["Disk Backup", "root-volume-expand-20260805T0332KST"], ["Activepieces", "6개 기존 Container Healthy"]], [42 * mm, 128 * mm]),
    Spacer(1, 6 * mm),
    p("Application 결함은 Reconciler를 중지하고 직전 Image로 Gateway만 롤백한다. DB와 Mirror Volume은 유지한다. Schema 제거는 Source Blob·Mirror 상태를 삭제할 수 있어 명시적 승인과 DB Backup 확인 없이는 수행하지 않는다."),
    callout("Password·Token·Provider Secret은 Repository, 보고서, Backup Archive에 저장하지 않았다."),
])

add_page(story, "9. 검토 항목과 다음 단계", [
    p("제품 책임자가 검토할 항목은 다음과 같다."),
    bullet("Repository 자료를 서버 로컬 Mirror에 유지하고 질의 시 GitHub에 의존하지 않는 원칙"),
    bullet("실제 갱신 주기 6시간과 Stale 기준 24시간"),
    bullet("7개 Mirror·9개 Profile·Reviewer dhslove의 승인 경계"),
    bullet("시험 서버 Root 1,005 GiB·가용 950 GiB 기준선"),
    bullet("#43 최초 Parser·Indexer Dry-run 대상 Profile과 Commit"),
    Spacer(1, 8 * mm),
    callout("다음 실행 단위: Issue #43 Parser·Chunk·Embeddings·FTS/Identifier/Vector·RRF·Lineage·삭제 전파", PALE, BLUE),
    Spacer(1, 7 * mm),
    p("Issue #42 PR 병합은 구현 승인이지 Source Version 승인과 동일하지 않다. 최초 Source 승인은 #43 Dry-run·부분 실패·원자 활성화 검증 뒤 별도로 수행한다."),
    Spacer(1, 7 * mm),
    p("관리 자산: docs/decisions/techflow-source-registry.json · docs/runbooks/source-registry-quarantine.md · output/issue-42-artifact-manifest.json", "small"),
], last=True)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
doc = BaseDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=20 * mm, leftMargin=20 * mm, topMargin=18 * mm, bottomMargin=20 * mm, title="TechFlow Issue #42 영속 Source 구현 완료", author="ABLESTACK TechFlow")
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
doc.addPageTemplates(PageTemplate(id="all", frames=frame, onPage=footer))
doc.build(story)
print(OUTPUT)
