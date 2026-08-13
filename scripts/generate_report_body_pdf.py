# -*- coding: utf-8 -*-
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

PROJECT_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = PROJECT_DIR.parents[1]
MD_FILE = ROOT_DIR / "参赛报告正文_MacroHub.md"
PDF_FILE = ROOT_DIR / "参赛报告正文_MacroHub.pdf"


def register_font():
    font_path = Path("C:/Windows/Fonts/msyh.ttc")
    bold_path = Path("C:/Windows/Fonts/msyhbd.ttc")
    if font_path.exists():
        pdfmetrics.registerFont(TTFont("CN", str(font_path)))
        pdfmetrics.registerFont(TTFont("CN-Bold", str(bold_path if bold_path.exists() else font_path)))
        return "CN", "CN-Bold"
    return "Helvetica", "Helvetica-Bold"


FONT, FONT_BOLD = register_font()


def styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"], fontName=FONT_BOLD, fontSize=20, leading=28, alignment=1, textColor=colors.HexColor("#123d7a"), spaceAfter=16),
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName=FONT_BOLD, fontSize=14, leading=22, textColor=colors.HexColor("#1d4f91"), spaceBefore=12, spaceAfter=6),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName=FONT_BOLD, fontSize=11.5, leading=18, textColor=colors.HexColor("#2563eb"), spaceBefore=8, spaceAfter=4),
        "body": ParagraphStyle("body", parent=base["BodyText"], fontName=FONT, fontSize=9.5, leading=15, spaceAfter=5),
        "code": ParagraphStyle("code", parent=base["Code"], fontName=FONT, fontSize=8, leading=11, leftIndent=12, backColor=colors.HexColor("#f1f5f9"), spaceAfter=5),
    }


def convert_line(line: str):
    line = line.strip()
    if not line:
        return Spacer(1, 0.12 * cm)
    line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    if line.startswith("# "):
        return Paragraph(line[2:], STYLES["title"])
    if line.startswith("## "):
        return Paragraph(line[3:], STYLES["h1"])
    if line.startswith("### "):
        return Paragraph(line[4:], STYLES["h2"])
    if line.startswith("- "):
        return Paragraph("• " + line[2:], STYLES["body"])
    if line.startswith("|"):
        return Paragraph(line, STYLES["code"])
    if line.startswith("```"):
        return Spacer(1, 0.05 * cm)
    return Paragraph(line, STYLES["body"])


STYLES = styles()


def main():
    lines = MD_FILE.read_text(encoding="utf-8").splitlines()
    story = [convert_line(line) for line in lines]
    doc = SimpleDocTemplate(str(PDF_FILE), pagesize=A4, rightMargin=1.5 * cm, leftMargin=1.5 * cm, topMargin=1.5 * cm, bottomMargin=1.2 * cm)
    doc.build(story)
    print(PDF_FILE)


if __name__ == "__main__":
    main()
