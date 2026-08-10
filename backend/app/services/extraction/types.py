from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class FileType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    DOC = "doc"
    TXT = "txt"
    RTF = "rtf"
    UNKNOWN = "unknown"


class ExtractionMethod(str, Enum):
    PDF_TEXT = "pdf_text"                      # pdfplumber, layout aware
    PDF_TEXT_FALLBACK = "pdf_text_fallback"    # pypdf, used when pdfplumber yields nothing
    DOCX = "docx"
    PLAIN_TEXT = "plain_text"
    OCR = "ocr"                                # deferred, see ocr.py
    NONE = "none"                              # nothing usable was extracted


class ExtractionWarning(str, Enum):
    EMPTY_FILE = "empty_file"
    UNSUPPORTED_TYPE = "unsupported_type"
    LEGACY_DOC_FORMAT = "legacy_doc_format"
    SCANNED_PDF_NEEDS_OCR = "scanned_pdf_needs_ocr"
    OCR_NOT_AVAILABLE = "ocr_not_available"
    LOW_TEXT_YIELD = "low_text_yield"
    PRIMARY_EXTRACTOR_FAILED = "primary_extractor_failed"
    ENCRYPTED_DOCUMENT = "encrypted_document"
    EXTRACTION_FAILED = "extraction_failed"


class ExtractionResult(BaseModel):
    """Outcome of turning an uploaded file into plain text.

    `text` is always a string, possibly empty. Callers check `ok` instead of
    trusting the text, so a failed extraction is never silently scored as a
    weak resume.
    """

    text: str = ""
    file_type: FileType = FileType.UNKNOWN
    method: ExtractionMethod = ExtractionMethod.NONE
    page_count: Optional[int] = None
    char_count: int = 0
    word_count: int = 0
    used_ocr: bool = False
    confidence: float = 0.0
    warnings: List[ExtractionWarning] = Field(default_factory=list)
    detail: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.method is not ExtractionMethod.NONE and self.char_count > 0

    def add_warning(self, warning: ExtractionWarning) -> None:
        if warning not in self.warnings:
            self.warnings.append(warning)
