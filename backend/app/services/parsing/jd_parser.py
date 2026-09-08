from typing import Any, Dict, Optional

from app.schemas.jd_structured import JDStructuredData
from app.services.parsing.jd_extractor_selector import JDExtractorSelector
from app.services.parsing.jd_url import company_from_url


class JDParserService:
    """Front door for turning job-description text into structured JSON."""

    def __init__(self, selector: Optional[JDExtractorSelector] = None):
        self.selector = selector or JDExtractorSelector()

    async def parse(self, text: str, url: Optional[str] = None) -> Dict[str, Any]:
        """Structure JD text. Returns the `JDStructuredData` shape.

        When the text names no company but a posting URL was supplied, recover
        the employer from the link (ATS slug or careers domain), so a bare paste
        with a URL still labels the analysis.
        """
        data = await self.parse_to_model(text)
        result = data.model_dump()
        if not result.get("company") and url:
            recovered = company_from_url(url)
            if recovered:
                result["company"] = recovered
        return result

    async def parse_to_model(self, text: str) -> JDStructuredData:
        return await self.selector.extract(text)
