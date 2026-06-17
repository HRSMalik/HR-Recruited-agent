import re
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Preformatted
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

PURPLE      = colors.HexColor("#5b2d8e")
PURPLE_LITE = colors.HexColor("#f4f0fb")
PURPLE_ROW  = colors.HexColor("#faf7ff")
WHITE       = colors.white
DARK        = colors.HexColor("#1a1a1a")
GREY        = colors.HexColor("#444444")
BORDER      = colors.HexColor("#e0d0f0")

PAGE_W, PAGE_H = A4
MARGIN = 20 * mm

def build_styles():
    base = getSampleStyleSheet()

    def s(name, **kw):
        return ParagraphStyle(name, **kw)

    return {
        "h1": s("h1", fontSize=24, leading=30, textColor=PURPLE, fontName="Helvetica-Bold",
                spaceAfter=2),
        "subtitle": s("subtitle", fontSize=10, leading=14, textColor=GREY, fontName="Helvetica",
                      spaceAfter=2),
        "h2": s("h2", fontSize=14, leading=20, textColor=PURPLE, fontName="Helvetica-Bold",
                spaceBefore=20, spaceAfter=6),
        "h3": s("h3", fontSize=11, leading=16, textColor=DARK, fontName="Helvetica-Bold",
                spaceBefore=14, spaceAfter=4),
        "h4": s("h4", fontSize=10, leading=14, textColor=DARK, fontName="Helvetica-Bold",
                spaceBefore=10, spaceAfter=3),
        "body": s("body", fontSize=10, leading=16, textColor=DARK, fontName="Helvetica",
                  spaceAfter=4),
        "bullet": s("bullet", fontSize=10, leading=15, textColor=DARK, fontName="Helvetica",
                    leftIndent=14, firstLineIndent=0, spaceAfter=2,
                    bulletIndent=4, bulletFontName="Helvetica"),
        "bullet2": s("bullet2", fontSize=10, leading=15, textColor=DARK, fontName="Helvetica",
                     leftIndent=28, firstLineIndent=0, spaceAfter=2,
                     bulletIndent=18, bulletFontName="Helvetica"),
        "code": s("code", fontSize=8.5, leading=13, textColor=DARK,
                  fontName="Courier", backColor=PURPLE_LITE,
                  leftIndent=10, rightIndent=10, spaceBefore=6, spaceAfter=6,
                  borderPadding=(6, 8, 6, 8)),
        "note": s("note", fontSize=9, leading=13, textColor=GREY, fontName="Helvetica-Oblique",
                  spaceAfter=4),
    }


def make_table(headers, rows):
    data = [headers] + rows
    col_count = len(headers)
    col_width = (PAGE_W - 2 * MARGIN) / col_count

    tbl = Table(data, colWidths=[col_width] * col_count, repeatRows=1)
    style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PURPLE),
        ("TEXTCOLOR",  (0, 0), (-1, 0), WHITE),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
        ("TOPPADDING",    (0, 0), (-1, 0), 7),
        ("FONTNAME",   (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",   (0, 1), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PURPLE_ROW]),
        ("GRID",       (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
    ])
    tbl.setStyle(style)
    return tbl


def parse_md(md_text, styles):
    story = []
    lines = md_text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]

        # Fenced code block
        if line.strip().startswith("```"):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            code = "\n".join(code_lines)
            story.append(Preformatted(code, styles["code"]))
            i += 1
            continue

        # HR
        if re.match(r"^---+$", line.strip()):
            story.append(Spacer(1, 4))
            story.append(HRFlowable(width="100%", thickness=0.8, color=BORDER))
            story.append(Spacer(1, 4))
            i += 1
            continue

        # Table
        if line.strip().startswith("|") and i + 1 < len(lines) and lines[i+1].strip().startswith("|---"):
            header_cells = [c.strip() for c in line.strip().strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                rows.append(cells)
                i += 1
            story.append(make_table(header_cells, rows))
            story.append(Spacer(1, 6))
            continue

        # H1
        if line.startswith("# ") and not line.startswith("## "):
            text = line[2:].strip()
            story.append(Paragraph(text, styles["h1"]))
            i += 1
            continue

        # H2
        if line.startswith("## ") and not line.startswith("### "):
            text = line[3:].strip()
            story.append(Spacer(1, 4))
            story.append(HRFlowable(width="100%", thickness=1.5, color=PURPLE))
            story.append(Spacer(1, 3))
            story.append(Paragraph(text, styles["h2"]))
            i += 1
            continue

        # H3
        if line.startswith("### ") and not line.startswith("#### "):
            text = line[4:].strip()
            story.append(Paragraph(text, styles["h3"]))
            i += 1
            continue

        # H4
        if line.startswith("#### "):
            text = line[5:].strip()
            story.append(Paragraph(text, styles["h4"]))
            i += 1
            continue

        # Subtitle lines (bold key: value)
        if line.startswith("**") and line.endswith("**") and ":" not in line[2:-2]:
            text = inline_format(line)
            story.append(Paragraph(text, styles["subtitle"]))
            i += 1
            continue

        # Sub-bullets (4-space or tab indent)
        if re.match(r"^    [-*] |^\t[-*] ", line):
            text = re.sub(r"^    [-*] |^\t[-*] ", "", line).strip()
            story.append(Paragraph(f"◦ {inline_format(text)}", styles["bullet2"]))
            i += 1
            continue

        # Bullets
        if re.match(r"^[-*] ", line) or re.match(r"^\d+\. ", line):
            text = re.sub(r"^[-*] |^\d+\. ", "", line).strip()
            story.append(Paragraph(f"• {inline_format(text)}", styles["bullet"]))
            i += 1
            continue

        # Empty line
        if line.strip() == "":
            story.append(Spacer(1, 5))
            i += 1
            continue

        # Normal paragraph
        if line.strip():
            story.append(Paragraph(inline_format(line.strip()), styles["body"]))

        i += 1

    return story


def inline_format(text):
    # Bold+italic
    text = re.sub(r"\*\*\*(.*?)\*\*\*", r"<b><i>\1</i></b>", text)
    # Bold
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    # Italic
    text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", text)
    # Inline code
    text = re.sub(r"`(.*?)`", r'<font name="Courier" color="#5b2d8e" backColor="#f4f0fb">\1</font>', text)
    return text


def generate(md_path, pdf_path):
    with open(md_path, "r") as f:
        md = f.read()

    styles = build_styles()

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        title="HR Recruited — PRD",
        author="HRSMalik",
    )

    story = parse_md(md, styles)
    doc.build(story)
    print(f"PDF saved: {pdf_path}")


if __name__ == "__main__":
    generate(
        "PRD.md",
        "[PRD] HR Recruited — Autonomous AI Recruitment System.pdf"
    )
