from io import BytesIO
from pathlib import Path

import pytest

from app.services.extraction.cleaner import clean_text, text_quality_ratio
from app.services.extraction.detector import detect_file_type
from app.services.extraction.pipeline import extract_document
from app.services.extraction.types import ExtractionMethod, ExtractionWarning, FileType

UPLOADS_DIR = Path(__file__).resolve().parents[1] / "uploads"


def _sample_pdfs():
    return sorted(UPLOADS_DIR.glob("*.pdf")) if UPLOADS_DIR.exists() else []


def _build_docx(paragraphs, table_rows=None) -> bytes:
    docx = pytest.importorskip("docx")
    document = docx.Document()
    for paragraph in paragraphs:
        document.add_paragraph(paragraph)
    if table_rows:
        table = document.add_table(rows=len(table_rows), cols=len(table_rows[0]))
        for row_index, row in enumerate(table_rows):
            for cell_index, value in enumerate(row):
                table.cell(row_index, cell_index).text = value
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


class TestDetector:
    def test_detects_pdf_from_magic_bytes_despite_wrong_extension(self):
        assert detect_file_type(b"%PDF-1.7\n...", "resume.txt") is FileType.PDF

    def test_detects_docx_by_inspecting_the_archive(self):
        assert detect_file_type(_build_docx(["hello"]), "resume.docx") is FileType.DOCX

    def test_plain_zip_is_not_mistaken_for_docx(self):
        import zipfile

        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("notes.txt", "hello")
        assert detect_file_type(buffer.getvalue(), "archive.zip") is FileType.UNKNOWN

    def test_detects_legacy_doc_container(self):
        assert detect_file_type(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1rest", "old.doc") is FileType.DOC

    def test_detects_plain_text(self):
        assert detect_file_type(b"Vishal Kumar\nPython", "resume.txt") is FileType.TXT

    def test_binary_noise_is_unknown(self):
        assert detect_file_type(b"\x00\x01\x02\x03", "mystery.bin") is FileType.UNKNOWN


class TestCleaner:
    def test_rejoins_line_wrapped_words(self):
        assert "production" in clean_text("produc-\ntion systems")

    def test_preserves_real_compound_words(self):
        assert "Retrieval-Augmented" in clean_text("Retrieval-\nAugmented generation")

    def test_normalizes_every_bullet_glyph(self):
        cleaned = clean_text("●First item\n   • Second item\n- Third item")
        assert cleaned.splitlines() == ["- First item", "- Second item", "- Third item"]

    def test_strips_zero_width_and_control_characters(self):
        assert clean_text("Vishal​Kumar\x07") == "VishalKumar"

    def test_collapses_excess_blank_lines(self):
        assert clean_text("A\n\n\n\n\nB") == "A\n\nB"

    def test_quality_ratio_flags_garbled_text(self):
        assert text_quality_ratio("Clean readable resume text.") > 0.95
        assert text_quality_ratio("�����") < 0.5


class TestPipeline:
    @pytest.mark.skipif(not _sample_pdfs(), reason="no sample PDFs available")
    def test_extracts_real_resume_pdfs(self):
        for path in _sample_pdfs():
            result = extract_document(path.read_bytes(), filename=path.name)

            assert result.ok, f"{path.name} failed to extract: {result.detail}"
            assert result.file_type is FileType.PDF
            assert result.method in (
                ExtractionMethod.PDF_TEXT,
                ExtractionMethod.PDF_TEXT_FALLBACK,
            )
            assert result.char_count > 500
            assert result.confidence > 0.5
            assert not result.used_ocr
            # The placeholder text the old parser produced must never reappear.
            assert "Binary or non-text content" not in result.text

    @pytest.mark.skipif(not _sample_pdfs(), reason="no sample PDFs available")
    def test_extracted_resume_contains_recognisable_content(self):
        result = extract_document(_sample_pdfs()[0].read_bytes(), filename="resume.pdf")
        lowered = result.text.lower()
        assert "@" in result.text, "expected an email address in the extracted text"
        assert any(term in lowered for term in ("experience", "education", "skills"))

    def test_extracts_docx_paragraphs_and_tables(self):
        payload = _build_docx(
            ["Vishal Kumar", "Senior Backend Engineer"],
            table_rows=[["Skills", "Python, FastAPI"]],
        )
        result = extract_document(payload, filename="resume.docx")

        assert result.ok
        assert result.file_type is FileType.DOCX
        assert result.method is ExtractionMethod.DOCX
        assert "Vishal Kumar" in result.text
        assert "Python, FastAPI" in result.text

    def test_extracts_plain_text(self):
        result = extract_document(b"Vishal Kumar\nPython and FastAPI", filename="resume.txt")
        assert result.ok
        assert result.method is ExtractionMethod.PLAIN_TEXT

    def test_empty_upload_is_reported_not_guessed(self):
        result = extract_document(b"", filename="resume.pdf")
        assert not result.ok
        assert ExtractionWarning.EMPTY_FILE in result.warnings

    def test_corrupt_pdf_is_reported_as_failed_not_scanned(self):
        result = extract_document(b"%PDF-1.4 this is not really a pdf", filename="broken.pdf")
        assert not result.ok
        assert ExtractionWarning.EXTRACTION_FAILED in result.warnings
        assert ExtractionWarning.SCANNED_PDF_NEEDS_OCR not in result.warnings

    def test_legacy_doc_is_rejected_with_guidance(self):
        result = extract_document(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1payload", filename="old.doc")
        assert not result.ok
        assert ExtractionWarning.LEGACY_DOC_FORMAT in result.warnings
        assert ".docx" in (result.detail or "")

    def test_unknown_binary_is_rejected(self):
        result = extract_document(b"\x00\x01\x02\x03\x04", filename="mystery.bin")
        assert not result.ok
        assert ExtractionWarning.UNSUPPORTED_TYPE in result.warnings
