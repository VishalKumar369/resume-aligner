from typing import Any, Dict, Optional

from app.schemas.structured import ResumeStructuredData
from app.services.extraction.pipeline import extract_document
from app.services.extraction.types import ExtractionResult
from app.services.parsing.extractor_selector import ResumeExtractorSelector


class ResumeParserService:
    """Front door for turning an uploaded resume into structured JSON.

    Text extraction lives in `app.services.extraction`; structuring lives in
    the extractor selector. This service just wires the two together so routes
    and the alignment scorer have one thing to call.
    """

    def __init__(self, selector: Optional[ResumeExtractorSelector] = None):
        self.selector = selector or ResumeExtractorSelector()

    async def parse(self, text: str) -> Dict[str, Any]:
        """Structure resume text. Returns the `ResumeStructuredData` shape."""
        data = await self.parse_to_model(text)
        return data.model_dump()

    async def parse_to_model(self, text: str) -> ResumeStructuredData:
        return await self.selector.extract(text)

    async def parse_bytes(
        self,
        file_bytes: bytes,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        extraction = self.extract(file_bytes, filename=filename, content_type=content_type)
        return await self.parse(extraction.text)

    def extract(
        self,
        file_bytes: bytes,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> ExtractionResult:
        """Turn an uploaded file into text via the shared extraction pipeline.

        Handles PDF and DOCX properly; callers must check `result.ok` before
        trusting the text.
        """
        return extract_document(file_bytes, filename=filename, content_type=content_type)
