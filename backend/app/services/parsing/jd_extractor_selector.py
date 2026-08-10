"""Chooses how a job description gets structured.

Mirrors the resume selector: the LLM is preferred when a key is configured but
is never load-bearing, so a JD upload cannot fail because of the provider.
"""

import logging
from typing import Optional

from app.schemas.jd_structured import JDStructuredData
from app.services.parsing.heuristic_jd_extractor import HeuristicJDExtractor
from app.services.parsing.llm_jd_extractor import LLMJDExtractor

logger = logging.getLogger(__name__)


class JDExtractorSelector:
    def __init__(
        self,
        heuristic: Optional[HeuristicJDExtractor] = None,
        llm: Optional[LLMJDExtractor] = None,
        prefer_llm: Optional[bool] = None,
    ):
        self.heuristic = heuristic or HeuristicJDExtractor()
        self.llm = llm or LLMJDExtractor()
        self._prefer_llm = prefer_llm

    async def extract(self, text: str) -> JDStructuredData:
        if not (text or "").strip():
            return self._empty_result()

        if self._should_try_llm():
            try:
                data = await self.llm.extract(text)
                data.extraction_meta.setdefault("extractor", self.llm.name)
                data.extraction_meta["fallback_used"] = False
                return data
            except Exception as exc:  # noqa: BLE001 - any failure must degrade, not raise
                logger.warning("LLM JD extraction failed, falling back to heuristic: %s", exc)
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
        return LLMJDExtractor.is_available()

    def _empty_result(self) -> JDStructuredData:
        data = JDStructuredData()
        data.extraction_meta = {
            "extractor": "none",
            "confidence": 0.0,
            "warnings": ["empty_text"],
        }
        return data
