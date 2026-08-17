"""Upload rejection paths for the resume endpoint.

The point of these tests is twofold: unsupported files must be turned away with
a helpful, specific message, and they must be turned away *cheaply* — before the
LLM structuring step (`ResumeParserService.parse`) or storage is ever touched.
"""

import uuid
from io import BytesIO
from types import SimpleNamespace

import pytest
from starlette.datastructures import Headers, UploadFile

from app.api.v1 import resume_routes
from app.services.extraction.detector import detect_file_type
from app.services.extraction.pipeline import extract_document
from app.services.extraction.types import ExtractionWarning, FileType

OWNER_ID = uuid.uuid4()

# A minimal but genuine PNG header: signature + the start of an IHDR chunk. The
# embedded null bytes are what mark it as binary rather than text.
PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01\x00\x00\x00\x01\x00"
JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x00\x00"


def _upload(payload: bytes, filename: str, content_type: str) -> UploadFile:
    return UploadFile(
        file=BytesIO(payload),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


def _stub_no_duplicate(monkeypatch):
    """Repo that finds no existing resume, and blows up if anything tries to persist."""

    class FakeRepo:
        def __init__(self, model, db):
            pass

        async def get_by_content_hash(self, owner_id, content_hash):
            return None

        async def create(self, *, obj_in):  # pragma: no cover - must not run
            raise AssertionError("an unsupported upload must never be stored")

    monkeypatch.setattr(resume_routes, "ResumeRepository", FakeRepo)


def _guard_expensive_work(monkeypatch):
    """Fail the test if the LLM structuring or storage runs for a rejected file."""

    async def _no_parse(self, text):  # pragma: no cover - must not run
        raise AssertionError("parse() ran for a file that should have been rejected first")

    def _no_storage(*args, **kwargs):  # pragma: no cover - must not run
        raise AssertionError("storage was touched for a rejected file")

    monkeypatch.setattr(resume_routes.ResumeParserService, "parse", _no_parse)
    monkeypatch.setattr(resume_routes, "get_storage", _no_storage)


class TestDetectorRejectsImages:
    """The cheap first line of defence: content sniffing, no extraction engine."""

    def test_png_is_unknown(self):
        assert detect_file_type(PNG_BYTES, "photo.png") is FileType.UNKNOWN

    def test_jpeg_is_unknown(self):
        assert detect_file_type(JPEG_BYTES, "scan.jpg") is FileType.UNKNOWN

    def test_extension_does_not_override_binary_content(self):
        # Even named .pdf, image bytes are not text and carry no PDF magic.
        assert detect_file_type(PNG_BYTES, "resume.pdf") is FileType.UNKNOWN


class TestPipelineSkipsExtractionForImages:
    def test_image_is_reported_unsupported_without_extraction(self):
        result = extract_document(PNG_BYTES, filename="photo.png")

        assert not result.ok
        assert result.file_type is FileType.UNKNOWN
        assert ExtractionWarning.UNSUPPORTED_TYPE in result.warnings
        # No page count / word count means no PDF or DOCX engine ran.
        assert result.page_count is None
        assert result.word_count == 0


class TestUploadRouteRejection:
    @pytest.mark.asyncio
    async def test_image_upload_is_rejected_with_415_before_parsing(self, monkeypatch):
        _stub_no_duplicate(monkeypatch)
        _guard_expensive_work(monkeypatch)

        with pytest.raises(Exception) as caught:
            await resume_routes.upload_resume(
                file=_upload(PNG_BYTES, "photo.png", "image/png"),
                label=None,
                db=None,
                owner_id=OWNER_ID,
            )

        assert getattr(caught.value, "status_code", None) == 415

    @pytest.mark.asyncio
    async def test_rejection_message_names_the_supported_formats(self, monkeypatch):
        _stub_no_duplicate(monkeypatch)
        _guard_expensive_work(monkeypatch)

        with pytest.raises(Exception) as caught:
            await resume_routes.upload_resume(
                file=_upload(JPEG_BYTES, "scan.jpg", "image/jpeg"),
                label=None,
                db=None,
                owner_id=OWNER_ID,
            )

        detail = getattr(caught.value, "detail", "")
        assert ".docx" in detail or "PDF" in detail

    @pytest.mark.asyncio
    async def test_oversize_file_is_rejected_with_413_before_any_work(self, monkeypatch):
        _stub_no_duplicate(monkeypatch)
        _guard_expensive_work(monkeypatch)

        oversize = b"%PDF-1.4" + b"0" * (resume_routes.MAX_UPLOAD_BYTES + 1)

        with pytest.raises(Exception) as caught:
            await resume_routes.upload_resume(
                file=_upload(oversize, "huge.pdf", "application/pdf"),
                label=None,
                db=None,
                owner_id=OWNER_ID,
            )

        assert getattr(caught.value, "status_code", None) == 413
