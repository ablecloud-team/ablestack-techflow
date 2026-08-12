from __future__ import annotations

from html import escape
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "docs/reports/issue-22-chat-community-approval-validation.md"
OUTPUT = ROOT / "output/pdf/techflow-chat-community-approval-report.pdf"
FONT_PATH = Path("C:/Windows/Fonts/malgun.ttf")
BOLD_PATH = Path("C:/Windows/Fonts/malgunbd.ttf")


def register_fonts() -> tuple[str, str]:
    regular, bold = "Helvetica", "Helvetica-Bold"
    if FONT_PATH.exists():
        pdfmetrics.registerFont(TTFont("Malgun", str(FONT_PATH)))
        regular = "Malgun"
    if BOLD_PATH.exists():
        pdfmetrics.registerFont(TTFont("Malgun-Bold", str(BOLD_PATH)))
        bold = "Malgun-Bold"
    return regular, bold


REGULAR, BOLD = register_fonts()


def inline(text: str) -> str:
    value = escape(text)
    value = re.sub(r"`([^`]+)`", r"<b>\1</b>", value)
    value = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"<link href='\2' color='#2563EB'>\1</link>", value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", value)
    return value


def page(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont(REGULAR, 8)
    canvas.setFillColor(colors.HexColor("#6B7280"))
    canvas.drawString(18 * mm, 10 * mm, "ABLESTACK TechFlow · Issue #22")
    canvas.drawRightString(192 * mm, 10 * mm, str(doc.page))
    canvas.restoreState()


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("TitleKR", parent=base["Title"], fontName=BOLD, fontSize=22, leading=30, textColor=colors.HexColor("#111827"), spaceAfter=10 * mm),
        "h1": ParagraphStyle("H1KR", parent=base["Heading1"], fontName=BOLD, fontSize=16, leading=22, textColor=colors.HexColor("#1D4ED8"), spaceBefore=7 * mm, spaceAfter=3 * mm),
        "h2": ParagraphStyle("H2KR", parent=base["Heading2"], fontName=BOLD, fontSize=12.5, leading=18, textColor=colors.HexColor("#111827"), spaceBefore=5 * mm, spaceAfter=2 * mm),
        "body": ParagraphStyle("BodyKR", parent=base["BodyText"], fontName=REGULAR, fontSize=9.3, leading=15, textColor=colors.HexColor("#1F2937"), spaceAfter=2.2 * mm),
        "bullet": ParagraphStyle("BulletKR", parent=base["BodyText"], fontName=REGULAR, fontSize=9.1, leading=14, leftIndent=5 * mm, firstLineIndent=-3 * mm, spaceAfter=1.3 * mm),
        "quote": ParagraphStyle("QuoteKR", parent=base["BodyText"], fontName=REGULAR, fontSize=8.8, leading=14, leftIndent=6 * mm, rightIndent=4 * mm, borderColor=colors.HexColor("#93C5FD"), borderWidth=1, borderPadding=5, backColor=colors.HexColor("#EFF6FF"), spaceAfter=2 * mm),
        "code": ParagraphStyle("CodeKR", parent=base["Code"], fontName=REGULAR, fontSize=7.8, leading=11, backColor=colors.HexColor("#F3F4F6"), borderPadding=5, spaceAfter=2 * mm),
    }


def table_from(lines: list[str], style: ParagraphStyle) -> Table:
    rows = [[Paragraph(inline(cell.strip()), style) for cell in line.strip().strip("|").split("|")] for line in lines]
    if len(rows) > 1:
        rows.pop(1)
    width = 174 * mm
    table = Table(rows, colWidths=[width / len(rows[0])] * len(rows[0]), repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), REGULAR),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
    ]))
    return table


def build_story() -> list:
    s = styles()
    story: list = []
    paragraph: list[str] = []
    table_lines: list[str] = []
    code_lines: list[str] = []
    in_code = False

    def flush_paragraph() -> None:
        if paragraph:
            story.append(Paragraph(inline(" ".join(paragraph)), s["body"]))
            paragraph.clear()

    def flush_table() -> None:
        if table_lines:
            story.append(table_from(table_lines, s["body"]))
            story.append(Spacer(1, 2 * mm))
            table_lines.clear()

    for raw in SOURCE.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if line.startswith("```"):
            flush_paragraph(); flush_table()
            if in_code:
                story.append(Paragraph(escape("\n".join(code_lines)).replace("\n", "<br/>"), s["code"]))
                code_lines.clear()
            in_code = not in_code
            continue
        if in_code:
            code_lines.append(line)
            continue
        if line.startswith("|"):
            flush_paragraph(); table_lines.append(line); continue
        flush_table()
        if not line:
            flush_paragraph(); continue
        if line.startswith("# "):
            flush_paragraph(); story.append(Paragraph(inline(line[2:]), s["title"])); continue
        if line.startswith("## "):
            flush_paragraph(); story.append(Paragraph(inline(line[3:]), s["h1"])); continue
        if line.startswith("### "):
            flush_paragraph(); story.append(Paragraph(inline(line[4:]), s["h2"])); continue
        if re.match(r"^[-*] ", line):
            flush_paragraph(); story.append(Paragraph("• " + inline(line[2:]), s["bullet"])); continue
        if re.match(r"^\d+\. ", line):
            flush_paragraph(); story.append(Paragraph(inline(line), s["bullet"])); continue
        if line.startswith(">"):
            flush_paragraph(); story.append(Paragraph(inline(line.lstrip("> ")), s["quote"])); continue
        paragraph.append(line)
    flush_paragraph(); flush_table()
    return story


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(str(OUTPUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=16 * mm, title="TechFlow Issue #22 Chat Community 승인 검증 보고서")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="body")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=page)])
    doc.build(build_story())
    print(f"report={OUTPUT}")


if __name__ == "__main__":
    main()
