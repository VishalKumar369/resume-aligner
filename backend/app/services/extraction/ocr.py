"""OCR fallback for scanned, image-only PDFs.

Deliberately not implemented yet. OCR needs system packages
(``apt install tesseract-ocr poppler-utils``) on top of pip dependencies, so it
was deferred out of the first extraction phase.

The pipeline already calls into this module whenever a PDF yields no text
layer. Implementing `run_ocr` here — and flipping `is_ocr_available` — is the
only change needed to switch scanned resumes on; no pipeline edits required.
"""

from typing import Optional


class OcrUnavailableError(RuntimeError):
    """Raised when OCR is needed but no OCR backend is installed."""


def is_ocr_available() -> bool:
    """Whether a working OCR backend is installed.

    Phase 1 ships without one; a scanned PDF is reported as a warning instead
    of silently producing an empty parse.
    """
    return False


def run_ocr(file_bytes: bytes, dpi: int = 300) -> Optional[str]:
    """Rasterise a PDF and OCR each page.

    Intended implementation: ``pdf2image.convert_from_bytes`` to render pages,
    then ``pytesseract.image_to_string`` per page.
    """
    raise OcrUnavailableError(
        "OCR is not installed. Install tesseract-ocr and poppler-utils, add "
        "pytesseract and pdf2image to requirements.txt, then implement run_ocr."
    )
