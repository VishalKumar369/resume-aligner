"""Export an optimized resume as plain text, .docx, and PDF.

All three render the same block list from `layout`, so they cannot drift.
Deliberately single column with no tables or graphics: that is what resume
parsers read reliably, and what the ATS `structural_safety` component rewards.

The .docx and the PDF share one page geometry and one typography spec (`STYLE`
below), and the .docx uses *exact* line spacing, so a line is the same height in
Word as it is in the PDF regardless of the installed font. That is what lets the
single-page condenser measure the PDF once and trust that the .docx fits too.
"""

from dataclasses import dataclass
from io import BytesIO
from typing import Any, Dict, List, Optional, Pattern, Tuple

from app.services.documents.keyword_highlight import segment_text
from app.services.documents.layout import BlockKind, build_blocks

# --------------------------------------------------------------- shared layout

# US Letter, in points (72pt = 1 inch). Both exporters use these exact values.
PAGE_WIDTH = 612.0
PAGE_HEIGHT = 792.0
MARGIN_TOP = 36.0      # 0.5"
MARGIN_BOTTOM = 36.0   # 0.5"
MARGIN_LEFT = 43.2     # 0.6"
MARGIN_RIGHT = 43.2    # 0.6"

# When *measuring* for the single-page condenser we reserve this much extra
# height, so a .docx that renders a hair taller than the PDF (font substitution,
# a bullet wrapping one line sooner) still lands on a single page in Word. The
# real downloaded documents use the full page.
MEASURE_HEADROOM = 40.0  # ~0.55"


@dataclass(frozen=True)
class BlockStyle:
    size: float
    leading: float
    space_before: float = 0.0
    space_after: float = 0.0
    bold: bool = False
    italic: bool = False
    center: bool = False
    color: Optional[str] = None  # "#RRGGBB"


# One typography definition consumed by both exporters. Change it here and the
# .docx and the PDF move together.
STYLE: Dict[BlockKind, BlockStyle] = {
    BlockKind.NAME: BlockStyle(18, 21, space_after=2, bold=True, center=True),
    BlockKind.CONTACT: BlockStyle(8.5, 11, space_after=2, center=True, color="#444444"),
    BlockKind.HEADING: BlockStyle(11, 13, space_before=10, space_after=3, bold=True),
    BlockKind.SUBHEADING: BlockStyle(10, 12, bold=True),
    BlockKind.META: BlockStyle(8.5, 10, space_after=2, italic=True, color="#555555"),
    BlockKind.PARAGRAPH: BlockStyle(9.5, 12, space_after=2),
    BlockKind.BULLET: BlockStyle(9.5, 12, space_after=2),
}


def _style_for(kind: BlockKind) -> BlockStyle:
    return STYLE.get(kind, STYLE[BlockKind.PARAGRAPH])


# ------------------------------------------------------------------- plain text


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


# ------------------------------------------------------------------------- docx


def render_docx(resume_data: Dict[str, Any], highlight_pattern: Optional[Pattern] = None) -> bytes:
    import docx
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
    from docx.shared import Pt, RGBColor

    def _rgb(hex_color: str) -> "RGBColor":
        return RGBColor(int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16))

    document = docx.Document()

    for section in document.sections:
        section.page_width = Pt(PAGE_WIDTH)
        section.page_height = Pt(PAGE_HEIGHT)
        section.top_margin = Pt(MARGIN_TOP)
        section.bottom_margin = Pt(MARGIN_BOTTOM)
        section.left_margin = Pt(MARGIN_LEFT)
        section.right_margin = Pt(MARGIN_RIGHT)

    # Arial is metrically close to the PDF's Helvetica, so line wrapping matches.
    # Zero the template's default paragraph spacing so nothing inherits Word's
    # 8pt-after, which would make the document run longer than the PDF.
    normal = document.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(STYLE[BlockKind.PARAGRAPH].size)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(0)

    for block in build_blocks(resume_data):
        spec = _style_for(block.kind)

        if block.kind is BlockKind.BULLET:
            # A real list style keeps list semantics for parsers; its spacing is
            # overridden below so its height matches the PDF's bullets.
            paragraph = document.add_paragraph(block.text, style="List Bullet")
        else:
            paragraph = document.add_paragraph()
            paragraph.add_run(block.text)

        for run in paragraph.runs:
            run.font.name = "Arial"
            run.font.size = Pt(spec.size)
            run.bold = spec.bold
            run.italic = spec.italic
            if spec.color:
                run.font.color.rgb = _rgb(spec.color)

        fmt = paragraph.paragraph_format
        fmt.space_before = Pt(spec.space_before)
        fmt.space_after = Pt(spec.space_after)
        # EXACTLY makes each line exactly `leading` points tall, so vertical
        # height is deterministic and equal to the PDF's leading.
        fmt.line_spacing = Pt(spec.leading)
        fmt.line_spacing_rule = WD_LINE_SPACING.EXACTLY
        if spec.center:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Bold the JD's keywords inside bullets, reusing the in-place highlighter so
    # the template and the preserved-file paths emphasise identically.
    if highlight_pattern is not None:
        from app.services.documents.docx_editor import highlight_bullets_in_docx
        highlight_bullets_in_docx(document, highlight_pattern)

    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


# -------------------------------------------------------------------------- pdf


def render_pdf(resume_data: Dict[str, Any], highlight_pattern: Optional[Pattern] = None) -> bytes:
    payload, _pages = render_pdf_with_page_count(resume_data, highlight_pattern=highlight_pattern)
    return payload


def render_pdf_with_page_count(
    resume_data: Dict[str, Any],
    measure_headroom: float = 0.0,
    highlight_pattern: Optional[Pattern] = None,
) -> Tuple[bytes, int]:
    """Render the PDF and report how many pages it occupies.

    `measure_headroom` shrinks the usable page height for the page-count only
    (see `MEASURE_HEADROOM`); the returned bytes are always a full-page render.
    """
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer

    base = getSampleStyleSheet()["Normal"]

    def _para_style(kind: BlockKind) -> ParagraphStyle:
        spec = _style_for(kind)
        font = "Helvetica-Bold" if spec.bold else "Helvetica-Oblique" if spec.italic else "Helvetica"
        style = ParagraphStyle(
            kind.value, parent=base, fontName=font,
            fontSize=spec.size, leading=spec.leading,
            spaceBefore=spec.space_before, spaceAfter=spec.space_after,
        )
        if spec.center:
            style.alignment = TA_CENTER
        if spec.color:
            style.textColor = spec.color
        return style

    styles = {kind: _para_style(kind) for kind in STYLE}

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=(PAGE_WIDTH, PAGE_HEIGHT),
        leftMargin=MARGIN_LEFT, rightMargin=MARGIN_RIGHT,
        topMargin=MARGIN_TOP, bottomMargin=MARGIN_BOTTOM + measure_headroom,
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
            markup = _highlight_markup(block.text, highlight_pattern)
            bullets.append(ListItem(Paragraph(markup, styles[BlockKind.BULLET]), leftIndent=12))
            continue

        flush_bullets()
        story.append(Paragraph(_escape(block.text), styles.get(block.kind, styles[BlockKind.PARAGRAPH])))

    flush_bullets()
    if not story:
        story.append(Spacer(1, 1))

    document.build(story)
    # reportlab increments `page` on every page break, so after build it holds
    # the total page count.
    return buffer.getvalue(), max(1, int(getattr(document, "page", 1)))


def count_pdf_pages(resume_data: Dict[str, Any], headroom: float = MEASURE_HEADROOM) -> int:
    """Pages the resume occupies (>= 1), with a safety headroom so the number is
    a floor the .docx honours too. Pass headroom=0 for the raw PDF page count."""
    return render_pdf_with_page_count(resume_data, measure_headroom=headroom)[1]


def _escape(text: str) -> str:
    """reportlab paragraphs accept inline markup, so raw text must be escaped."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _highlight_markup(text: str, pattern: Optional[Pattern]) -> str:
    """Escaped reportlab markup with the JD's keyword matches wrapped in <b>."""
    if pattern is None:
        return _escape(text)
    return "".join(
        f"<b>{_escape(chunk)}</b>" if is_keyword else _escape(chunk)
        for chunk, is_keyword in segment_text(text, pattern)
    )
