#!/usr/bin/env python3
"""Build the Issue #74 Community operations report PDF."""

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
SOURCE = ROOT / "docs/evidence/issue-74/community-operations-validation.json"
OUTPUT = ROOT / "output/pdf/techflow-community-operations-report.pdf"
FONT, BOLD = "MalgunGothic", "MalgunGothicBold"
pdfmetrics.registerFont(TTFont(FONT, "C:/Windows/Fonts/malgun.ttf"))
pdfmetrics.registerFont(TTFont(BOLD, "C:/Windows/Fonts/malgunbd.ttf"))

INK, GRAY = colors.HexColor("#15253E"), colors.HexColor("#52647D")
LINE, BLUE = colors.HexColor("#D5E1F1"), colors.HexColor("#155EEF")
PALE, GREEN, YELLOW = colors.HexColor("#EAF2FF"), colors.HexColor("#078248"), colors.HexColor("#FFF6DF")
base = getSampleStyleSheet()
styles = {
    "meta": ParagraphStyle("meta", parent=base["Normal"], fontName=BOLD, fontSize=8.5, leading=12, textColor=GRAY),
    "title": ParagraphStyle("title", parent=base["Title"], fontName=BOLD, fontSize=24, leading=33, textColor=INK),
    "subtitle": ParagraphStyle("subtitle", parent=base["Normal"], fontName=FONT, fontSize=11, leading=18, textColor=GRAY),
    "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName=BOLD, fontSize=16, leading=23, textColor=INK, spaceAfter=4*mm),
    "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName=BOLD, fontSize=12, leading=18, textColor=INK, spaceBefore=2*mm, spaceAfter=2*mm),
    "body": ParagraphStyle("body", parent=base["BodyText"], fontName=FONT, fontSize=9, leading=14.5, textColor=colors.HexColor("#30343B"), spaceAfter=2.2*mm),
    "small": ParagraphStyle("small", parent=base["BodyText"], fontName=FONT, fontSize=7.5, leading=11, textColor=GRAY),
    "table": ParagraphStyle("table", parent=base["BodyText"], fontName=FONT, fontSize=7.5, leading=10.5, textColor=colors.HexColor("#30343B")),
    "table_head": ParagraphStyle("table_head", parent=base["BodyText"], fontName=BOLD, fontSize=7.5, leading=10.5, textColor=colors.white),
}


def para(value: object, style: str = "body") -> Paragraph:
    return Paragraph(escape(str(value)).replace("\n", "<br/>"), styles[style])


def make_table(rows: list[list[object]], widths: list[float]) -> Table:
    cells = [[para(cell, "table_head" if row_index == 0 else "table") for cell in row] for row_index, row in enumerate(rows)]
    item = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
    item.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#243B64")), ("GRID", (0,0), (-1,-1), .35, LINE),
        ("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 5),
        ("RIGHTPADDING", (0,0), (-1,-1), 5), ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5), ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F7F9FC")]),
    ]))
    return item


def callout(value: str, color=GREEN, background=PALE) -> Table:
    item = Table([[para(value)]], colWidths=[174*mm])
    item.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),background),("BOX",(0,0),(-1,-1),1.25,color),
                              ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
                              ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8)]))
    return item


def footer(canvas, doc) -> None:
    canvas.saveState(); canvas.setFont(FONT, 7); canvas.setFillColor(GRAY)
    canvas.drawString(18*mm, 10*mm, "ABLESTACK TechFlow - Issue #74")
    canvas.drawRightString(192*mm, 10*mm, f"{doc.page:02d}"); canvas.restoreState()


data = json.loads(SOURCE.read_text(encoding="utf-8"))
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
doc = BaseDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=16*mm, bottomMargin=17*mm,
                      title="TechFlow Issue #74 Community 백업·모니터링·보안 운영 강화 완료 보고서", author="ABLESTACK TechFlow")
doc.addPageTemplates([PageTemplate(id="normal", frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="content")], onPage=footer)])

story = [
    Spacer(1, 19*mm), para("ABLESTACK TECHFLOW · ISSUE #74", "meta"), Spacer(1, 8*mm),
    para("Community 백업·모니터링·보안\n운영 강화 완료 보고서", "title"), Spacer(1, 6*mm),
    para("운영 Flarum을 일관된 암호화 백업, 5분 관측, Chat 경보와 보안 정책으로 보호하고 WSL에서 전체 복원을 실증한 결과입니다.", "subtitle"),
    Spacer(1, 17*mm), callout("GO - 운영 적용 완료 · UI Theme 활성 · 전체 복원 9초 · 데이터 차이 0건"),
    Spacer(1, 8*mm), para("검증일 2026-08-19 · Flarum 1.8.18 · Ubuntu 24.04", "meta"), PageBreak(),

    para("1. 완료 판단", "h1"),
    make_table([["항목","결과","판정"], ["자동 백업","매일 03:20 KST · 무결성 검증","PASS"],
                ["암호화","OpenPGP · 운영 공개키만","PASS"], ["외부 복사","179,701,760 Byte WSL Vault","PASS"],
                ["격리 복원","32 Table · 11,336 File · 9초","PASS"], ["관측·Chat","5분 · 전이 2회 · 운영 HTTP 200","PASS"],
                ["보안","Header·TLS·Rate Limit·권한·로그","PASS"], ["운영 UI","Theme·한글·OAuth 아이콘","PASS"]], [49*mm, 88*mm, 37*mm]),
    Spacer(1, 7*mm), callout("Nginx·PHP-FPM·MariaDB 3/3 Active · HTTP 200/200/200 · Disk 2% · Alert 0", BLUE), PageBreak(),

    para("2. 백업 설계와 일관성", "h1"),
    make_table([["단계","처리","안전 장치"], ["1","PHP-FPM 쓰기 정지","Trap으로 항상 재시작"],
                ["2","MariaDB 논리 Dump","Single transaction·Trigger·Event"], ["3","App·설정·업로드 Snapshot","Cache·Log 제외"],
                ["4","PHP-FPM 즉시 재개","정지 구간 최소화"], ["5","공개키 암호화","평문 즉시 제거"],
                ["6","Manifest·SHA-256","완성 Directory만 latest"]], [24*mm, 75*mm, 75*mm]),
    Spacer(1, 6*mm), para("운영 서버에는 공개키만 두고 개인키와 Passphrase는 WSL 복구 Vault에 root:root 0600으로 보관합니다."),
    Spacer(1, 4*mm), callout("정기 RPO 24시간+10분 · 운영 보존 30일 · 실패 .partial 자동 제거", GREEN), PageBreak(),

    para("3. 운영 Backup과 WSL 전체 복원", "h1"),
    make_table([["검증","값"], ["운영 Backup","community-20260819T095245Z"], ["암호화 파일","Database·Application 2개"],
                ["WSL 외부 복사","171.4 MiB"], ["복원 범위","별도 App Root·DB"], ["복원 Table·File","32 / 11,336"],
                ["RTO","9초"], ["격리 HTTP","200 · 0.947초"]], [65*mm, 109*mm]),
    Spacer(1, 6*mm), make_table([["데이터","원본","복원"], ["사용자",41,41], ["토론",121,121], ["게시물",325,325], ["첨부",115,115]], [82*mm, 46*mm, 46*mm]),
    Spacer(1, 5*mm), callout("운영 Snapshot 생성 135초 뒤 검증 · 핵심 데이터 차이 0건 · 평문 복원 자원 정리", GREEN), PageBreak(),

    para("4. 관측과 Chat 경보", "h1"),
    make_table([["영역","수집 항목","정상 기준"], ["서비스","Nginx·PHP-FPM·MariaDB","3/3 Active"],
                ["HTTP","Community Local/Public·AI","200/200/200"], ["용량","Disk·inode·Upload Bytes","70% Warning / 85% Critical"],
                ["백업","나이·Integrity","30시간 이내·true"], ["로그","최근 5분 Critical 행","0"],
                ["보안","Mail Driver","smtp"]], [42*mm, 79*mm, 53*mm]),
    Spacer(1, 6*mm), para("동일 Fingerprint는 1시간 동안 억제하고 상태 변화 시 장애·복구를 각각 한 번 전송합니다. WSL Mock 시험은 장애→동일 장애→복구에서 2회만 전송했고 운영 Chat 시험은 HTTP 200이었습니다."),
    Spacer(1, 4*mm), callout("Backup Lock 중 Monitor는 건너뛰어 계획된 PHP-FPM 정지를 장애로 오인하지 않습니다.", BLUE), PageBreak(),

    para("5. 보안 검증", "h1"),
    make_table([["항목","결과"], ["외부 HTTPS","HTTP/2 200 · 인증서 검증 0"], ["Header","nosniff·SAMEORIGIN·Referrer·Permissions·HSTS"],
                ["TLS","1.0 차단 · 1.2 허용"], ["Auth Rate Limit","40회 중 27회 HTTP 429"],
                ["config.php","root:www-data 0640"], ["Ops·Chat 설정","root:root 0600"],
                ["World-writable File","0건"], ["Logrotate·Secret Scan","PASS · 0건"], ["보안 갱신 Timer","enabled / active"]], [67*mm, 107*mm]),
    Spacer(1, 6*mm), callout("질문·첨부 원문, Password, Token, API Key는 관측·관리 Backup·보고서에 기록하지 않습니다.", GREEN), PageBreak(),

    para("6. Symfony Mailer 잔여 위험", "h1"),
    para("Composer Audit에는 CVE-2026-45068 1건이 남아 있습니다. 공식 권고의 취약 경로는 SendmailTransport가 수신자를 명령행 인자로 처리하는 경우입니다."),
    make_table([["구분","정책"], ["현재 전송","smtp만 허용"], ["자동 확인","5분마다 mail_driver 검사"],
                ["위반","Critical Chat 경보"], ["패치 전략","상위 Flarum 호환 확보 시 Symfony 안전 버전 교체"]], [54*mm, 120*mm]),
    Spacer(1, 6*mm), callout("위험을 제거했다고 주장하지 않고 사용하지 않는 취약 실행 경로를 지속 감시합니다.", colors.HexColor("#9A6700"), YELLOW),
    Spacer(1, 7*mm), para("공식 참고: https://symfony.com/cve-2026-45068", "small"), PageBreak(),

    para("7. 롤백과 운영 판정", "h1"),
    para("Nginx 적용 전 설정은 /var/backups/techflow-flarum/security-20260819T091120Z에 보관했습니다. 관측 Timer는 독립적으로 중지할 수 있고 Nginx는 백업 파일 복원 후 nginx -t와 HTTP 200으로 검증합니다. 운영 DB와 App Root에는 자동 복원하지 않습니다."),
    make_table([["변경","범위"], ["변경","Community Script·Timer·Nginx 정책·파일 권한"],
                ["미변경","질문·답변·첨부·Flarum Schema·Activepieces·AI Gateway"],
                ["보호 유지","GitHub→Chat Webhook 조회·배포·재시작·설정 변경 없음"]], [49*mm, 125*mm]),
    Spacer(1, 7*mm), callout("Issue #74 완료 · 승인된 Community Theme 운영 활성 · 판정 GO", GREEN),
    Spacer(1, 7*mm), para("다음 운영 단계", "h2"),
    para("회사 승인 Object Storage 또는 Backup Vault에 같은 암호화 Archive를 복제하고 분기마다 전체 복원 훈련을 반복합니다."),
    para("근거 자산", "h2"),
    para("ADR: docs/adr/0010-community-backup-observability-security.md\nRunbook: docs/runbooks/community-backup-monitor-security.md\n완료 보고서: docs/reports/issue-74-community-operations-validation.md\n구조화 증적: docs/evidence/issue-74/community-operations-validation.json", "small"),
]
doc.build(story)
print(OUTPUT)
