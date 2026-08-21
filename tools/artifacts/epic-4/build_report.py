#!/usr/bin/env python3
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
DATA = json.loads((ROOT / "docs/evidence/epic-4/production-e2e.json").read_text(encoding="utf-8"))
OUTPUT = ROOT / "output/pdf/techflow-epic4-assist-validation-report.pdf"
FONT, BOLD = "MalgunGothic", "MalgunGothicBold"
pdfmetrics.registerFont(TTFont(FONT, "C:/Windows/Fonts/malgun.ttf"))
pdfmetrics.registerFont(TTFont(BOLD, "C:/Windows/Fonts/malgunbd.ttf"))

INK, GRAY, LINE = colors.HexColor("#15253E"), colors.HexColor("#52647D"), colors.HexColor("#D5E1F1")
BLUE, GREEN, PALE = colors.HexColor("#155EEF"), colors.HexColor("#078248"), colors.HexColor("#EAF2FF")
base = getSampleStyleSheet()
S = {
    "meta": ParagraphStyle("meta", parent=base["Normal"], fontName=BOLD, fontSize=8.5, leading=12, textColor=GRAY),
    "title": ParagraphStyle("title", parent=base["Title"], fontName=BOLD, fontSize=24, leading=33, textColor=INK),
    "subtitle": ParagraphStyle("subtitle", parent=base["Normal"], fontName=FONT, fontSize=11, leading=18, textColor=GRAY),
    "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName=BOLD, fontSize=16, leading=23, textColor=INK, spaceAfter=4*mm),
    "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName=BOLD, fontSize=12, leading=18, textColor=INK, spaceAfter=2*mm),
    "body": ParagraphStyle("body", parent=base["BodyText"], fontName=FONT, fontSize=9, leading=14.5, textColor=colors.HexColor("#30343B"), spaceAfter=2.4*mm),
    "small": ParagraphStyle("small", parent=base["BodyText"], fontName=FONT, fontSize=7.5, leading=11, textColor=GRAY),
    "cell": ParagraphStyle("cell", parent=base["BodyText"], fontName=FONT, fontSize=7.5, leading=10.5, textColor=colors.HexColor("#30343B")),
    "head": ParagraphStyle("head", parent=base["BodyText"], fontName=BOLD, fontSize=7.5, leading=10.5, textColor=colors.white),
}

def p(value: object, style: str = "body") -> Paragraph:
    return Paragraph(escape(str(value)).replace("\n", "<br/>"), S[style])

def table(rows: list[list[object]], widths: list[float]) -> Table:
    cells = [[p(value, "head" if index == 0 else "cell") for value in row] for index, row in enumerate(rows)]
    result = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
    result.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#243B64")), ("GRID", (0,0), (-1,-1), .35, LINE),
        ("VALIGN", (0,0), (-1,-1), "TOP"), ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F7F9FC")]),
        ("LEFTPADDING", (0,0), (-1,-1), 5), ("RIGHTPADDING", (0,0), (-1,-1), 5),
        ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    return result

def callout(value: str, color=GREEN) -> Table:
    result = Table([[p(value)]], colWidths=[174*mm])
    result.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),PALE),("BOX",(0,0),(-1,-1),1.2,color),
                                ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
                                ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8)]))
    return result

def footer(canvas, doc):
    canvas.saveState(); canvas.setFont(FONT, 7); canvas.setFillColor(GRAY)
    canvas.drawString(18*mm, 10*mm, "ABLESTACK TechFlow - Epic #4")
    canvas.drawRightString(192*mm, 10*mm, f"{doc.page:02d}"); canvas.restoreState()

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
doc = BaseDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=16*mm, bottomMargin=17*mm,
                      title="TechFlow Epic #4 Assist 실증 완료 보고서", author="ABLESTACK TechFlow")
doc.addPageTemplates([PageTemplate(id="normal", frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="content")], onPage=footer)])

chat, community, runtime, continuity = DATA["chatE2E"], DATA["communityE2E"], DATA["runtime"], DATA["continuityE2E"]
story = [
    Spacer(1, 20*mm), p("ABLESTACK TECHFLOW · EPIC #4", "meta"), Spacer(1, 8*mm),
    p("Chat·Community Assist\n운영 실증 완료 보고서", "title"), Spacer(1, 6*mm),
    p("문서와 제품 코드를 종합하는 AI 지원, 연속 대화, 자동 게시, 장애 복구와 비식별 KPI를 실제 운영 경로에서 검증한 결과입니다.", "subtitle"),
    Spacer(1, 16*mm), callout("GO · Gateway 0.15.0 · Community·Chat·Activepieces 정상 · 보호 Webhook 변경 0건"),
    Spacer(1, 8*mm), p("2026-08-21 · Ubuntu 24.04 · OpenAI Responses API", "meta"), PageBreak(),

    p("1. 완료 판단", "h1"),
    table([["영역","실증 결과","판정"], ["Repository","271 tests · CRLF 0 · OpenAPI 39","PASS"],
           ["Chat",f"답변 {chat['firstAnswerLength']:,}/{chat['secondAnswerLength']:,}자 · 4 Turn · RESOLVED","PASS"],
           ["Community",f"Discussion #{community['discussionId']} → Post #{community['publishedPostId']} 자동 게시","PASS"],
           ["연속성",f"장애 {continuity['failureNotificationCount']}회 · 복구 {continuity['recoveryNotificationCount']}회 · 정상 알림 0","PASS"],
           ["공개 서비스","Community·Chat·Activepieces HTTP 200","PASS"],
           ["보호 서비스","Container·Image·StartedAt 변화 0","PASS"]], [42*mm, 96*mm, 36*mm]),
    Spacer(1, 7*mm), callout("Gateway Healthy · Poller Running · 처리 유실 0 · 내부 근거 노출 0", BLUE), PageBreak(),

    p("2. Chat 직접 기술지원", "h1"),
    p("사용자별 Conversation과 Context Version을 유지해 첫 질문의 환경을 후속 질문에서 이어서 검토합니다. 답변은 DOC, ABLESTACK Diplo, 관련 제품 코드, ABLESTACK Europa Preview 순서로 종합하고 정보가 부족하면 필요한 로그·화면·환경 정보를 요청합니다."),
    table([["단계","결과"], ["첫 질문",f"{chat['firstAnswerLength']:,}자 전문 엔지니어 답변"],
           ["후속 질문",f"{chat['secondAnswerLength']:,}자 · 같은 Context"], ["대화 기록",f"User·Assistant {chat['turns']} Turn"],
           ["종료",f"{chat['contextStateAfterResolve']} · Context Version {chat['contextVersion']}"]], [55*mm,119*mm]),
    Spacer(1, 6*mm), callout("일반 답변에는 Repository·Branch·Commit·Path·Line·Evidence ID를 표시하지 않습니다."), PageBreak(),

    p("3. Community 자동 답변과 연속성", "h1"),
    p("운영 Poller는 내부 Flarum 주소에서 새 글과 후속 글을 수집하고 공개 HTTPS 링크를 사용자에게 제공합니다. 성공한 Post만 체크포인트하며 실패한 Post는 같은 Event·멱등 키로 다시 처리합니다."),
    table([["항목","운영 실증"], ["Discussion",f"#{community['discussionId']} 운영 시험 글"],
           ["Case",community["caseId"]], ["AI 게시",f"Post #{community['publishedPostId']} · {community['publishedContentLength']:,}자"],
           ["안전 출력",f"내부 근거 노출 {community['internalEvidenceExposed']}"], ["정리","시험 Discussion만 삭제"]], [48*mm,126*mm]),
    Spacer(1, 6*mm), callout(f"기동 직후 실패 {runtime['communityPoller']['startupFailuresObserved']}회 뒤 정상 Poll {runtime['communityPoller']['completedCyclesObserved']}회 · 체크포인트 유실 없음"), PageBreak(),

    p("4. 실패 복구·알림·KPI", "h1"),
    table([["정책","구현"], ["재시도","지수 백오프 1·2·4초"], ["Dead Letter","기본 3회 실패 후 분리"],
           ["수동 재처리","Failure ID를 RETRYING으로 전환"], ["멱등성","Event·Post·Chat post_id 중복 수렴"],
           ["알림","최초 장애 1회, 실제 복구 1회"], ["정상 상태","주기 알림 0회"],
           ["KPI","원문·로그·Source 경로 없는 비식별 집계"]], [55*mm,119*mm]),
    Spacer(1, 6*mm), callout("통제 장애 → OPEN → RECOVERED · Chat 알림 실패 0건", GREEN), PageBreak(),

    p("5. 배포와 보호 경계", "h1"),
    p(f"배포 전 소스·Compose 설정·DB를 {DATA['release']['backupRoot']}에 백업했습니다. Gateway와 Community Poller만 새 이미지로 교체했고 GitHub→Chat Event Gateway와 Activepieces App·Worker는 재기동하지 않았습니다."),
    table([["서비스","최종 상태"], ["AI Gateway",f"{DATA['release']['image']} · {runtime['gateway']['state']}"],
           ["Community Poller",f"{DATA['release']['image']} · {runtime['communityPoller']['state']}"],
           ["Community","HTTP 200"], ["Chat","HTTP 200"], ["Activepieces","HTTP 200"]], [63*mm,111*mm]),
    Spacer(1, 6*mm), callout("보호 대상 3개 서비스의 Container ID·Image ID·StartedAt이 배포 전후 동일합니다.", GREEN), PageBreak(),

    p("6. Epic #5 제품화 준비", "h1"),
    p("Epic #5는 사내 실증을 ABLESTACK Assist MVP로 전환합니다. 고객·파트너·엔지니어가 Community, Chat, 제품 UI에서 동일 Case와 해결 상태를 사용하도록 만들며 실제 자원 변경은 별도 Ops 승인 경계로 유지합니다."),
    table([["작업군","완료 기준"], ["Tenant·RBAC","교차 노출 0 · 보존/삭제 검증"],
           ["SSO·채널 Identity","세 채널 권한·Case 상태 일치"], ["Release 지식 수명주기","적용 버전 확정 · Preview 오표현 0"],
           ["제품 UI Assist","질문·Artifact·대화·해결 UX"], ["HA·SLO·보안","99.9% 목표 · 복구 훈련"],
           ["Pilot·Beta Gate","답변 90% · 올바른 보류 95%"]], [58*mm,116*mm]),
    Spacer(1, 7*mm), callout("최초 착수: Tenant·RBAC 경계 + 제품 UX 계약 Architecture Baseline", BLUE),
    Spacer(1, 7*mm), p("근거 자산", "h2"),
    p("docs/evidence/epic-4/production-e2e.json\ndocs/runbooks/epic4-service-continuity.md\ndocs/plans/epic5-assist-mvp-plan.md", "small"),
]
doc.build(story)
print(OUTPUT)
