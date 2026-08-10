"""Chooses how a resume gets structured.

The LLM extractor is preferred when a provider key is configured, but it is
never load-bearing: any failure - missing key, network error, bad JSON, schema
violation - degrades to the deterministic heuristic extractor rather than
failing the upload.
"""

import logging
from typing import Optional

from app.schemas.structured import ResumeStructuredData
from app.services.parsing.heuristic_resume_extractor import HeuristicResumeExtractor
from app.services.parsing.llm_resume_extractor import LLMResumeExtractor

logger = logging.getLogger(__name__)


class ResumeExtractorSelector:
    def __init__(
        self,
        heuristic: Optional[HeuristicResumeExtractor] = None,
        llm: Optional[LLMResumeExtractor] = None,
        prefer_llm: Optional[bool] = None,
    ):
        self.heuristic = heuristic or HeuristicResumeExtractor()
        self.llm = llm or LLMResumeExtractor()
        # None means "decide from configuration at call time".
        self._prefer_llm = prefer_llm

    async def extract(self, text: str) -> ResumeStructuredData:
        if not (text or "").strip():
            return self._empty_result()

        if self._should_try_llm():
            try:
                data = await self.llm.extract(text)
                data.extraction_meta.setdefault("extractor", self.llm.name)
                data.extraction_meta["fallback_used"] = False
                return data
            except Exception as exc:  # noqa: BLE001 - any failure must degrade, not raise
                logger.warning("LLM extraction failed, falling back to heuristic: %s", exc)
                data = self.heuristic.extract(text)
                data.extraction_meta["fallback_used"] = True
                data.extraction_meta["fallback_reason"] = str(exc)[:200]
                return data

        data = self.heuristic.extract(text)
        data.extraction_meta["fallback_used"] = False
        data.extraction_meta["llm_available"] = False
        return data

    def _should_try_llm(self) -> bool:
        if self._prefer_llm is not None:
            return self._prefer_llm
        return LLMResumeExtractor.is_available()

    def _empty_result(self) -> ResumeStructuredData:
        data = ResumeStructuredData()
        data.extraction_meta = {
            "extractor": "none",
            "confidence": 0.0,
            "warnings": ["empty_text"],
        }
        return data
