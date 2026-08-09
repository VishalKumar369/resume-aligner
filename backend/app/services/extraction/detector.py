import os
import zipfile
from io import BytesIO
from typing import Optional

from app.services.extraction.types import FileType

# Signatures are checked before the filename, because browsers and clients lie
# about Content-Type and users rename files.
_PDF_MAGIC = b"%PDF"
_ZIP_MAGIC = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"  # legacy .doc / .xls container
_RTF_MAGIC = b"{\\rtf"

_EXTENSION_MAP = {
    ".pdf": FileType.PDF,
    ".docx": FileType.DOCX,
    ".doc": FileType.DOC,
    ".rtf": FileType.RTF,
    ".txt": FileType.TXT,
    ".md": FileType.TXT,
    ".text": FileType.TXT,
}


def detect_file_type(file_bytes: bytes, filename: Optional[str] = None) -> FileType:
    """Identify a document from its content, falling back to the extension."""
    if not file_bytes:
        return FileType.UNKNOWN

    head = file_bytes[:8]

    if head.startswith(_PDF_MAGIC):
        return FileType.PDF
    if head.startswith(_OLE_MAGIC):
        return FileType.DOC
    if head.startswith(_RTF_MAGIC):
        return FileType.RTF
    if head.startswith(_ZIP_MAGIC):
        return FileType.DOCX if _is_docx_archive(file_bytes) else FileType.UNKNOWN

    by_extension = _EXTENSION_MAP.get(os.path.splitext(filename or "")[1].lower())
    if by_extension in (FileType.TXT, FileType.RTF):
        return by_extension

    return FileType.TXT if _looks_like_text(file_bytes) else FileType.UNKNOWN


def _is_docx_archive(file_bytes: bytes) -> bool:
    """A .docx is a zip holding word/document.xml; .xlsx and .pptx are not."""
    try:
        with zipfile.ZipFile(BytesIO(file_bytes)) as archive:
            return "word/document.xml" in archive.namelist()
    except (zipfile.BadZipFile, OSError):
        return False


def _looks_like_text(file_bytes: bytes) -> bool:
    sample = file_bytes[:4096]
    if b"\x00" in sample:
        return False
    try:
        sample.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False
