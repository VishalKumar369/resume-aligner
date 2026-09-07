"""Optimize a resume by editing the user's own .docx in place.

Rebuilding from structured data (``writers.py``) yields an ATS-clean but generic
document: it drops the colours, fonts, hyperlinks, and layout the user designed.
When the upload is a .docx we can instead edit that very file — replacing only
the bullet text the optimizer rewrote — so everything else the user styled
(header links, section colours, spacing) is preserved exactly.

A matching PDF is produced by converting the edited .docx with LibreOffice when
it is installed; callers fall back to the template renderer when it is not.
"""

import os
import re
import shutil
import subprocess
import tempfile
from io import BytesIO
from typing import List, Optional, Tuple


def _norm(text: str) -> str:
    """Whitespace- and case-insensitive key for matching a bullet to a paragraph."""
    return re.sub(r"\s+", " ", (text or "").strip()).lower()


def apply_rewrites_to_docx(
    original: bytes, rewrites: List[Tuple[str, str]]
) -> Tuple[bytes, int]:
    """Return (edited_docx_bytes, replacements_applied).

    Each (before, after) rewrite replaces the text of the paragraph whose text
    matches ``before``, keeping that paragraph's own run formatting and style.
    Only matched paragraphs change; hyperlinks and styling elsewhere are left
    untouched. ``replacements_applied`` is 0 when nothing matched, letting the
    caller fall back to the template renderer.
    """
    import docx  # imported lazily; python-docx is a heavy import

    document = docx.Document(BytesIO(original))
    wanted = {_norm(before): after for before, after in rewrites if before and after}
    applied = 0

    if wanted:
        for paragraph in _iter_paragraphs(document):
            replacement = wanted.get(_norm(paragraph.text))
            if replacement is not None and _replace_paragraph_text(paragraph, replacement):
                applied += 1

    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue(), applied


def _iter_paragraphs(document):
    """Every paragraph in the body and in any tables (some resumes use tables)."""
    yield from document.paragraphs
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                yield from cell.paragraphs


def _replace_paragraph_text(paragraph, new_text: str) -> bool:
    """Set a paragraph's text to ``new_text`` while keeping its first run's
    formatting (font, size, weight, colour) and the paragraph's list style.

    The whole new string goes into the first run and the remaining runs are
    blanked, so the bullet keeps its look without duplicating mixed inline
    formatting we cannot faithfully re-segment.
    """
    runs = paragraph.runs
    if not runs:
        return False
    runs[0].text = new_text
    for run in runs[1:]:
        run.text = ""
    return True


def docx_to_pdf(docx_bytes: bytes, timeout: float = 60.0) -> Optional[bytes]:
    """Convert .docx bytes to PDF bytes with LibreOffice; None if unavailable.

    Keeping the conversion here means the preserved-format .docx and its PDF are
    the same document, instead of the PDF silently falling back to the template.
    """
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return None

    with tempfile.TemporaryDirectory() as tmp:
        source = os.path.join(tmp, "resume.docx")
        with open(source, "wb") as handle:
            handle.write(docx_bytes)
        try:
            subprocess.run(
                [soffice, "--headless", "--convert-to", "pdf", "--outdir", tmp, source],
                check=True,
                capture_output=True,
                timeout=timeout,
            )
        except (subprocess.SubprocessError, OSError):
            return None

        output = os.path.join(tmp, "resume.pdf")
        if not os.path.exists(output):
            return None
        with open(output, "rb") as handle:
            return handle.read()
