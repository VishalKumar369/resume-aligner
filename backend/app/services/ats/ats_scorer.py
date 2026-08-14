"""ATS scoring entry point.

The deterministic engine always runs and is the score of record. When an API
key is configured, an LLM pass may add extra prose feedback - it can never
change the number, so scores stay reproducible.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from app.schemas.analytics import ATSScoreSchema
from app.services.ai.factory import AIFactory
from app.services.ats.ats_engine import ATSResult, DeterministicATSEngine

logger = logging.getLogger(__name__)

MAX_FEEDBACK_ITEMS = 6


class ATSScorerService:
    def __init__(self, engine: Optional[DeterministicATSEngine] = None, provider=None):
        self.engine = engine or DeterministicATSEngine()
        self._provider = provider

    def compute(
        self,
        resume_data: Dict[str, Any],
        jd_data: Optional[Dict[str, Any]] = None,
        resume_text: str = "",
        extraction_meta: Optional[Dict[str, Any]] = None,
    ) -> ATSResult:
        """Deterministic score. No network, no key, reproducible."""
        return self.engine.score(
            resume_data=resume_data,
            jd_data=jd_data,
            resume_text=resume_text,
            extraction_meta=extraction_meta,
        )

    async def compute_with_feedback(
        self,
        resume_data: Dict[str, Any],
        jd_data: Optional[Dict[str, Any]] = None,
        resume_text: str = "",
        jd_text: str = "",
        extraction_meta: Optional[Dict[str, Any]] = None,
    ) -> ATSResult:
        """Deterministic score, optionally enriched with LLM prose feedback."""
        result = self.compute(resume_data, jd_data, resume_text, extraction_meta)

        if not (self._provider or AIFactory.is_available()):
            return result

        try:
            extra = await self._llm_feedback(resume_text, jd_text)
        except Exception as exc:  # noqa: BLE001 - feedback is optional, never fatal
            logger.warning("ATS feedback enrichment failed: %s", exc)
            return result

        result.formatting_feedback = self._merge(
            result.formatting_feedback, extra.get("formatting_feedback")
        )
        result.content_feedback = self._merge(
            result.content_feedback, extra.get("content_feedback")
        )
        return result

    def to_schema(self, result: ATSResult) -> ATSScoreSchema:
        return ATSScoreSchema(
            score=result.score,
            breakdown=result.breakdown,
            formatting_feedback=result.formatting_feedback,
            content_feedback=result.content_feedback,
        )

    # ---------------------------------------------------------------- internals

    async def _llm_feedback(self, resume_text: str, jd_text: str) -> Dict[str, Any]:
        provider = self._provider or AIFactory.get_provider()
        prompt = (
            "Review this resume against the job description for ATS readability and "
            "content quality. Return ONLY a JSON object:\n"
            '{"formatting_feedback": [str], "content_feedback": [str]}\n'
            "Each item must be one specific, actionable sentence. Do not invent scores.\n\n"
            f"RESUME:\n{(resume_text or '')[:4000]}\n\n"
            f"JOB DESCRIPTION:\n{(jd_text or '')[:4000]}"
        )

        raw = await provider.chat_completion(
            [{"role": "user", "content": prompt}], temperature=0.2, json_mode=True
        )
        start, end = (raw or "").find("{"), (raw or "").rfind("}")
        if start == -1 or end <= start:
            return {}

        parsed = json.loads(raw[start:end + 1])
        return parsed if isinstance(parsed, dict) else {}

    def _merge(self, base: List[str], extra: Optional[Any]) -> List[str]:
        merged = list(base)
        for item in extra or []:
            text = str(item).strip()
            if text and text not in merged:
                merged.append(text)
        return merged[:MAX_FEEDBACK_ITEMS]
