import logging
from io import BytesIO
from typing import List, Optional, Tuple

from app.services.extraction.types import ExtractionMethod, ExtractionWarning

logger = logging.getLogger(__name__)


class PdfExtractionOutput:
    def __init__(
        self,
        text: str,
        method: ExtractionMethod,
        page_count: Optional[int],
        warnings: List[ExtractionWarning],
        detail: Optional[str] = None,
    ):
        self.text = text
        self.method = method
        self.page_count = page_count
        self.warnings = warnings
        self.detail = detail


def extract_pdf(file_bytes: bytes) -> PdfExtractionOutput:
    """Pull the text layer out of a PDF.

    pdfplumber is the primary engine because it preserves reading order on the
    two-column layouts resumes favour. pypdf runs as a fallback when pdfplumber
    returns nothing, since the two disagree on some generator quirks.
    """
    warnings: List[ExtractionWarning] = []

    text, page_count, error = _extract_with_pdfplumber(file_bytes)
    if text.strip():
        return PdfExtractionOutput(text, ExtractionMethod.PDF_TEXT, page_count, warnings)

    if error:
        warnings.append(ExtractionWarning.PRIMARY_EXTRACTOR_FAILED)
        logger.warning("pdfplumber extraction failed: %s", error)

    fallback_text, fallback_pages, fallback_error, encrypted = _extract_with_pypdf(file_bytes)
    if encrypted:
        warnings.append(ExtractionWarning.ENCRYPTED_DOCUMENT)

    if fallback_text.strip():
        return PdfExtractionOutput(
            fallback_text,
            ExtractionMethod.PDF_TEXT_FALLBACK,
            fallback_pages or page_count,
            warnings,
        )

    detail = error or fallback_error
    return PdfExtractionOutput(
        "",
        ExtractionMethod.NONE,
        fallback_pages or page_count,
        warnings,
        detail,
    )


def _extract_with_pdfplumber(file_bytes: bytes) -> Tuple[str, Optional[int], Optional[str]]:
    try:
        import pdfplumber
    except ImportError as exc:
        return "", None, f"pdfplumber unavailable: {exc}"

    try:
        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
            return "\n".join(pages), len(pdf.pages), None
    except Exception as exc:  # noqa: BLE001 - any malformed PDF must fall through
        return "", None, str(exc)


def _extract_with_pypdf(file_bytes: bytes) -> Tuple[str, Optional[int], Optional[str], bool]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        return "", None, f"pypdf unavailable: {exc}", False

    encrypted = False
    try:
        reader = PdfReader(BytesIO(file_bytes))
        if reader.is_encrypted:
            encrypted = True
            # Many resumes are encrypted with an empty owner password, which
            # still permits extraction.
            try:
                reader.decrypt("")
            except Exception as exc:  # noqa: BLE001
                return "", None, f"encrypted PDF could not be opened: {exc}", encrypted

        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages), len(reader.pages), None, encrypted
    except Exception as exc:  # noqa: BLE001
        return "", None, str(exc), encrypted
