from typing import Any, Dict, Optional

from app.schemas.jd_structured import JDStructuredData
from app.services.parsing.jd_extractor_selector import JDExtractorSelector


class JDParserService:
    """Front door for turning job-description text into structured JSON."""

    def __init__(self, selector: Optional[JDExtractorSelector] = None):
        self.selector = selector or JDExtractorSelector()

    async def parse(self, text: str) -> Dict[str, Any]:
        """Structure JD text. Returns the `JDStructuredData` shape."""
        data = await self.parse_to_model(text)
        return data.model_dump()

    async def parse_to_model(self, text: str) -> JDStructuredData:
        return await self.selector.extract(text)
