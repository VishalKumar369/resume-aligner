import logging
from typing import Optional

from app.services.extraction import ocr
from app.services.extraction.cleaner import clean_text, text_quality_ratio
from app.services.extraction.detector import detect_file_type
from app.services.extraction.docx_extractor import extract_docx
from app.services.extraction.pdf_extractor import extract_pdf
from app.services.extraction.text_extractor import extract_plain_text
from app.services.extraction.types import (
    ExtractionMethod,
    ExtractionResult,
    ExtractionWarning,
    FileType,
)

logger = logging.getLogger(__name__)

# A resume with fewer characters than this almost certainly failed to extract
# rather than genuinely being that short.
MIN_USABLE_CHARS = 120

# Below this share of ordinary characters the text layer is garbled.
MIN_QUALITY_RATIO = 0.80


class DocumentExtractionService:
    """Turns uploaded bytes into clean text plus an honest quality report."""

    def extract(
        self,
        file_bytes: bytes,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> ExtractionResult:
        if not file_bytes:
            result = ExtractionResult(detail="Uploaded file is empty")
            result.add_warning(ExtractionWarning.EMPTY_FILE)
            return result

        file_type = detect_file_type(file_bytes, filename)
        result = ExtractionResult(file_type=file_type)

        if file_type is FileType.PDF:
            self._extract_pdf(file_bytes, result)
        elif file_type is FileType.DOCX:
            self._extract_docx(file_bytes, result)
        elif file_type is FileType.TXT:
            self._set_text(result, extract_plain_text(file_bytes), ExtractionMethod.PLAIN_TEXT)
        elif file_type is FileType.DOC:
            result.add_warning(ExtractionWarning.LEGACY_DOC_FORMAT)
            result.detail = "Legacy .doc files are not supported. Please upload a PDF or .docx."
        elif file_type is FileType.RTF:
            result.add_warning(ExtractionWarning.UNSUPPORTED_TYPE)
            result.detail = "RTF files are not supported. Please upload a PDF or .docx."
        else:
            result.add_warning(ExtractionWarning.UNSUPPORTED_TYPE)
            result.detail = f"Unrecognised file format for '{filename or 'upload'}'."

        self._finalize(result)
        return result

    def _extract_pdf(self, file_bytes: bytes, result: ExtractionResult) -> None:
        output = extract_pdf(file_bytes)
        result.page_count = output.page_count
        for warning in output.warnings:
            result.add_warning(warning)

        if output.text.strip():
            self._set_text(result, output.text, output.method)
            return

        if output.page_count is None:
            # Neither engine could open the file, so it is damaged or not
            # really a PDF - OCR would not help. The engine's own message is
            # logged rather than surfaced, since it means nothing to a user.
            logger.warning("PDF could not be opened: %s", output.detail)
            result.add_warning(ExtractionWarning.EXTRACTION_FAILED)
            result.detail = "This PDF could not be read. It may be corrupted or password protected."
            return

        # The PDF opened but carries no text layer: it is a scan or image export.
        result.add_warning(ExtractionWarning.SCANNED_PDF_NEEDS_OCR)
        self._try_ocr(file_bytes, result)

    def _extract_docx(self, file_bytes: bytes, result: ExtractionResult) -> None:
        text, error = extract_docx(file_bytes)
        if text.strip():
            self._set_text(result, text, ExtractionMethod.DOCX)
            return

        result.add_warning(ExtractionWarning.EXTRACTION_FAILED)
        result.detail = error or "No readable text found in the document."

    def _try_ocr(self, file_bytes: bytes, result: ExtractionResult) -> None:
        if not ocr.is_ocr_available():
            result.add_warning(ExtractionWarning.OCR_NOT_AVAILABLE)
            result.detail = (
                "This PDF has no text layer (it looks like a scan or an image). "
                "OCR is not enabled yet - please upload a text-based PDF or a .docx."
            )
            return

        try:
            text = ocr.run_ocr(file_bytes)
        except ocr.OcrUnavailableError as exc:
            result.add_warning(ExtractionWarning.OCR_NOT_AVAILABLE)
            result.detail = str(exc)
            return
        except Exception as exc:  # noqa: BLE001 - OCR failure must not 500
            logger.warning("OCR failed: %s", exc)
            result.add_warning(ExtractionWarning.EXTRACTION_FAILED)
            result.detail = f"OCR failed: {exc}"
            return

        if text and text.strip():
            self._set_text(result, text, ExtractionMethod.OCR)
            result.used_ocr = True

    def _set_text(self, result: ExtractionResult, raw: str, method: ExtractionMethod) -> None:
        cleaned = clean_text(raw)
        result.text = cleaned
        result.method = method if cleaned else ExtractionMethod.NONE

    def _finalize(self, result: ExtractionResult) -> None:
        result.char_count = len(result.text)
        result.word_count = len(result.text.split())

        if not result.text:
            result.confidence = 0.0
            return

        quality = text_quality_ratio(result.text)
        if quality < MIN_QUALITY_RATIO:
            result.add_warning(ExtractionWarning.EXTRACTION_FAILED)
            result.detail = result.detail or "Extracted text appears garbled."
        if result.char_count < MIN_USABLE_CHARS:
            result.add_warning(ExtractionWarning.LOW_TEXT_YIELD)

        result.confidence = self._score_confidence(result, quality)

    def _score_confidence(self, result: ExtractionResult, quality: float) -> float:
        """Blend text volume with character quality into a 0-1 signal."""
        volume = min(1.0, result.char_count / 1500)
        score = (quality * 0.6) + (volume * 0.4)

        if result.method is ExtractionMethod.PDF_TEXT_FALLBACK:
            score *= 0.9
        if result.used_ocr:
            score *= 0.75
        if ExtractionWarning.LOW_TEXT_YIELD in result.warnings:
            score *= 0.5

        return round(min(1.0, max(0.0, score)), 3)


_service = DocumentExtractionService()


def extract_document(
    file_bytes: bytes,
    filename: Optional[str] = None,
    content_type: Optional[str] = None,
) -> ExtractionResult:
    """Module-level entry point for the shared extraction service."""
    return _service.extract(file_bytes, filename=filename, content_type=content_type)
