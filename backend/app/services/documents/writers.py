"""Export an optimized resume as plain text, .docx, and PDF.

All three render the same block list from `layout`, so they cannot drift.
Deliberately single column with no tables or graphics: that is what resume
parsers read reliably, and what the ATS `structural_safety` component rewards.
"""

from io import BytesIO
from typing import Any, Dict, List

from app.services.documents.layout import Block, BlockKind, build_blocks


def render_text(resume_data: Dict[str, Any]) -> str:
    """Plain-text rendering, used for keyword scoring of a generated resume."""
    lines: List[str] = []
    for block in build_blocks(resume_data):
        if block.kind is BlockKind.HEADING:
            lines.extend(["", block.text])
        elif block.kind is BlockKind.BULLET:
            lines.append(f"- {block.text}")
        else:
            lines.append(block.text)
    return "\n".join(lines).strip()


def render_docx(resume_data: Dict[str, Any]) -> bytes:
    import docx
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt, RGBColor

    document = docx.Document()

    for section in document.sections:
        section.top_margin = section.bottom_margin = Pt(36)
        section.left_margin = section.right_margin = Pt(45)

    normal = document.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10)

    for block in build_blocks(resume_data):
        if block.kind is BlockKind.NAME:
            paragraph = document.add_paragraph()
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = paragraph.add_run(block.text)
            run.bold = True
            run.font.size = Pt(18)

        elif block.kind is BlockKind.CONTACT:
            paragraph = document.add_paragraph()
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = paragraph.add_run(block.text)
            run.font.size = Pt(9)
            run.font.color.rgb = RGBColor(0x44, 0x44, 0x44)

        elif block.kind is BlockKind.HEADING:
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.space_before = Pt(10)
            paragraph.paragraph_format.space_after = Pt(2)
            run = paragraph.add_run(block.text)
            run.bold = True
            run.font.size = Pt(11)

        elif block.kind is BlockKind.SUBHEADING:
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.space_after = Pt(0)
            run = paragraph.add_run(block.text)
            run.bold = True

        elif block.kind is BlockKind.META:
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.space_after = Pt(2)
            run = paragraph.add_run(block.text)
            run.italic = True
            run.font.size = Pt(9)
            run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

        elif block.kind is BlockKind.BULLET:
            # A real list style, so parsers see list semantics rather than a
            # hand-typed dash.
            paragraph = document.add_paragraph(block.text, style="List Bullet")
            paragraph.paragraph_format.space_after = Pt(1)

        else:
            document.add_paragraph(block.text)

    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def render_pdf(resume_data: Dict[str, Any]) -> bytes:
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer

    base = getSampleStyleSheet()["Normal"]
    styles = {
        "name": ParagraphStyle("name", parent=base, fontName="Helvetica-Bold",
                               fontSize=18, leading=21, alignment=TA_CENTER, spaceAfter=2),
        "contact": ParagraphStyle("contact", parent=base, fontSize=8.5, leading=11,
                                  alignment=TA_CENTER, textColor="#444444", spaceAfter=2),
        "heading": ParagraphStyle("heading", parent=base, fontName="Helvetica-Bold",
                                  fontSize=11, leading=13, spaceBefore=10, spaceAfter=3),
        "subheading": ParagraphStyle("subheading", parent=base, fontName="Helvetica-Bold",
                                     fontSize=10, leading=12, spaceAfter=0),
        "meta": ParagraphStyle("meta", parent=base, fontName="Helvetica-Oblique",
                               fontSize=8.5, leading=10, textColor="#555555", spaceAfter=2),
        "body": ParagraphStyle("body", parent=base, fontSize=9.5, leading=12, spaceAfter=2),
    }

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=LETTER,
        leftMargin=0.6 * inch, rightMargin=0.6 * inch,
        topMargin=0.5 * inch, bottomMargin=0.5 * inch,
        title=str((resume_data.get("personal_info") or {}).get("name") or "Resume"),
    )

    story: List[Any] = []
    bullets: List[ListItem] = []

    def flush_bullets() -> None:
        if bullets:
            story.append(ListFlowable(
                list(bullets), bulletType="bullet", start="•",
                leftIndent=12, bulletFontSize=7, spaceAfter=2,
            ))
            bullets.clear()

    for block in build_blocks(resume_data):
        if block.kind is BlockKind.BULLET:
            bullets.append(ListItem(Paragraph(_escape(block.text), styles["body"]), leftIndent=12))
            continue

        flush_bullets()
        style_name = {
            BlockKind.NAME: "name",
            BlockKind.CONTACT: "contact",
            BlockKind.HEADING: "heading",
            BlockKind.SUBHEADING: "subheading",
            BlockKind.META: "meta",
        }.get(block.kind, "body")
        story.append(Paragraph(_escape(block.text), styles[style_name]))

    flush_bullets()
    if not story:
        story.append(Spacer(1, 1))

    document.build(story)
    return buffer.getvalue()


def _escape(text: str) -> str:
    """reportlab paragraphs accept inline markup, so raw text must be escaped."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
