#!/usr/bin/env python3
"""Build the Issue #44 implementation and validation report PDF."""

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
OUTPUT = ROOT / "output/pdf/techflow-grounded-responses-report.pdf"
FONT, BOLD = "MalgunGothic", "MalgunGothicBold"
pdfmetrics.registerFont(TTFont(FONT, "C:/Windows/Fonts/malgun.ttf"))
pdfmetrics.registerFont(TTFont(BOLD, "C:/Windows/Fonts/malgunbd.ttf"))
BLACK, GRAY = colors.HexColor("#101010"), colors.HexColor("#5B616B")
LINE, BLUE, PALE = colors.HexColor("#D4D8DF"), colors.HexColor("#3D8DFF"), colors.HexColor("#DDF3FF")
GREEN = colors.HexColor("#117A4B")
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


def grid(rows, widths):
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


def callout(text, color=BLUE):
    item = Table([[p(text, "callout")]], colWidths=[174 * mm])
    item.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE), ("BOX", (0, 0), (-1, -1), 1.2, color),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return item


def footer(canvas, doc):
    canvas.saveState(); canvas.setFont(FONT, 7); canvas.setFillColor(GRAY)
    canvas.drawString(18 * mm, 10 * mm, "ABLESTACK TechFlow · Issue #44")
    canvas.drawRightString(192 * mm, 10 * mm, f"{doc.page:02d}"); canvas.restoreState()


OUTPUT.parent.mkdir(parents=True, exist_ok=True)
doc = BaseDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
                      topMargin=16 * mm, bottomMargin=17 * mm,
                      title="TechFlow Issue #44 근거 기반 Responses 구현 완료 보고서", author="ABLESTACK TechFlow")
doc.addPageTemplates([PageTemplate(id="normal", frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="content")], onPage=footer)])

story = [Spacer(1, 17 * mm), p("ABLESTACK TECHFLOW · ISSUE #44", "meta"), Spacer(1, 9 * mm),
         p("OpenAI Responses·근거 답변\n구현 및 시험 서버 실증 완료", "title"), Spacer(1, 6 * mm),
         p("검색 근거, 모델 선택, 안전한 보류, 장애와 복구를 하나의 AI Gateway 운영 계약으로 구현했습니다.", "subtitle"),
         Spacer(1, 18 * mm), callout("96 + 96 Tests · Real ANSWERED 5 Citations · Secret Scan 0 · Rollback Verified"),
         Spacer(1, 8 * mm), p("TechFlow AI Gateway 0.4.0 · OpenAI Responses API · 2026-08-10", "meta"), PageBreak()]

story += [p("1. 완료 판정", "h1"), p("Issue #44의 코드, 실 Provider, 서버 배포, 감사, 보류, 복구와 문서 자산화를 완료했습니다."),
          grid([["검증", "결과", "판정"], ["Gateway", "0.4.0 · Database/Vector ready", "PASS"],
                ["실 답변", "ANSWERED · Citation 5", "PASS"], ["사전 보류", "ABSTAINED · Generation 호출 없음", "PASS"],
                ["테스트", "로컬 96 · 서버 격리 96", "PASS"], ["Secret", "배포 파일·로그 Hit 0", "PASS"],
                ["복구", "0.4 → 0.3 → 0.4", "PASS"]], [38 * mm, 101 * mm, 35 * mm]),
          Spacer(1, 6 * mm), callout("Issue #44 구현 기준은 충족했습니다. PR 병합 전까지 Issue는 열어 두고 검토 자산으로 제공합니다.", GREEN), PageBreak()]

story += [p("2. 답변 처리 구조", "h1"),
          grid([["단계", "입력", "판정·출력"], ["Retrieve", "질문·Scope", "최대 10개 D0 Chunk · RRF"],
                ["Preflight", "Source·Branch·Commit", "보류 또는 승인 Profile"], ["Generate", "최소 Context", "Strict JSON Schema"],
                ["Postvalidate", "Citation IDs", "부분집합·Branch·Test-only 재검증"], ["Return", "검증 결과", "ANSWERED·ABSTAINED·FAILED"]],
               [34 * mm, 64 * mm, 76 * mm]), Spacer(1, 5 * mm),
          bullet("원본 Repository는 OpenAI File·Vector Store에 업로드하지 않습니다."),
          bullet("모델은 스스로 라우팅하지 않으며 Gateway가 검색 Metadata로 한 번 결정합니다."),
          bullet("실패나 낮은 확신을 이유로 Terra에서 Sol로 자동 이중 호출하지 않습니다."),
          bullet("반환 Citation이 전달 Context에 없으면 답변을 ABSTAINED로 바꿉니다."), PageBreak()]

story += [p("3. Provider·보안 계약", "h1"),
          grid([["항목", "고정값"], ["Default", "gpt-5.6-terra · medium · 단일 Repository/Commit"],
                ["Escalation", "gpt-5.6-sol · high · 승인된 복수 Repository/Commit"],
                ["Responses", "store=false · background=false · stream=false · tools=[]"],
                ["Output", "Strict JSON Schema"], ["Identity", "HMAC-SHA256 safety_identifier · 최대 64자"],
                ["Audit", "Model·Request/Response ID·Token·Latency·Status·Error"],
                ["Raw retention", "질문·Chunk·답변 0"]], [42 * mm, 132 * mm]),
          Spacer(1, 5 * mm), callout("GitHub에는 OPENAI_API_KEY와 OPENAI_PROJECT_ID Secret 이름만 존재하며 실제 값은 문서·PR·로그에 남기지 않습니다."), PageBreak()]

story += [p("4. 실증 증거", "h1"),
          grid([["항목", "결과"], ["실 답변", "기본 Profile · Citation 5 · 6,184 ms"],
                ["Usage", "Input 6,002 · Output 620 Token"], ["사전 보류", "CLOUD_MAIN 근거 없음 · Generation 미호출"],
                ["활성 Source", "GENIE_MASTER · ACTIVE"], ["검색 자산", "34 File · 64 Chunk · 64 Embedding"],
                ["코드 구조", "15 Symbol · 45 Relation"], ["Activepieces", "6 Container 모두 Healthy"],
                ["Disk", "1,005 GiB · 가용 950 GiB · 사용률 2%"]], [42 * mm, 132 * mm]),
          Spacer(1, 5 * mm), p("Canary는 답변 원문을 출력하지 않고 State, Profile, Citation 수, Answer 문자 수와 호출 여부만 기록했습니다.", "small"), PageBreak()]

story += [p("5. 실 Provider에서 발견한 결함", "h1"),
          grid([["결함", "관측", "수정"], ["가명 식별자", "67자 · HTTP 400", "HMAC 출력 최대 64자"],
                ["과대 라우팅", "동일 Version 문서+코드를 Sol로 승격", "단일 Repository/Commit은 Terra"],
                ["상향 Timeout", "Sol/high · 12초 정책 초과", "승격 조건을 복수 구성요소로 한정"]], [43 * mm, 68 * mm, 63 * mm]),
          Spacer(1, 6 * mm), bullet("첫 실패는 PROVIDER_REJECTED/TERMINAL로 감사했습니다."),
          bullet("두 번째 실패는 PROVIDER_TIMEOUT/RETRYABLE로 감사했습니다."),
          bullet("오류 원문, 질문, Context와 답변은 감사 테이블에 저장하지 않았습니다."),
          bullet("수정 후 같은 실 데이터 경로에서 ANSWERED를 확인했습니다."),
          Spacer(1, 6 * mm), callout("문서와 코드가 함께 검색됐다는 사실은 충돌이 아닙니다. Repository·Commit 경계를 모델 비용과 지연의 결정 기준으로 사용합니다.", GREEN), PageBreak()]

story += [p("6. 배포와 복구", "h1"),
          grid([["단계", "자산·결과"], ["Backup", "DB Dump · 기존 Image ID · Compose · Override · Checksum"],
                ["Stage", "별도 경로 빌드 · Network-none 96 Tests"], ["Deploy", "issue-44 Image · Gateway 0.4.0 Healthy"],
                ["Rollback", "issue-43 Image · Gateway 0.3.0 Healthy"], ["Forward", "issue-44 Image 복귀 · Database/Vector ready"],
                ["Data", "34/64/64/15/45 보존"]], [42 * mm, 132 * mm]),
          Spacer(1, 5 * mm), p("최초 백업 경로", "h2"),
          p("/home/ablecloud/techflow-ai-gateway/backups/issue44-predeploy-20260810T0230KST", "small"),
          Spacer(1, 5 * mm), bullet("Base Compose와 OpenAI 운영자 Override를 항상 함께 지정합니다."),
          bullet("Schema 추가가 없어 Image와 Compose 참조만으로 롤백했습니다."),
          bullet("Activepieces Volume과 여섯 Container는 변경하지 않았습니다."), PageBreak()]

story += [p("7. 운영 확인과 다음 단계", "h1"),
          p("OpenAI 공식 문서상 store=false는 애플리케이션 저장을 끄지만 그 자체가 Zero Data Retention을 보장하지 않습니다. Project의 ZDR 또는 Modified Abuse Monitoring 적용 상태는 Organization Dashboard에서 운영자가 확인해야 합니다."),
          grid([["구분", "조치"], ["Data Controls", "D1 이상 확장 전 ZDR/MAM 적용 상태 확인"],
                ["Credential", "대화에 직접 입력된 현재 API Key 회전"], ["Issue #44", "Draft PR 검토·병합 후 종료"],
                ["Issue #45", "Activepieces Push·승인·재색인 Flow 연동"]], [44 * mm, 130 * mm]),
          Spacer(1, 7 * mm), callout("현재 상태: IMPLEMENTED · DEPLOYED · REAL-PROVIDER VALIDATED · ROLLBACK VERIFIED", GREEN),
          Spacer(1, 7 * mm), p("참고", "h2"),
          p("https://developers.openai.com/api/docs/guides/latest-model", "small"),
          p("https://developers.openai.com/api/docs/guides/structured-outputs", "small"),
          p("https://developers.openai.com/api/docs/guides/your-data", "small")]

doc.build(story)
print(OUTPUT)
