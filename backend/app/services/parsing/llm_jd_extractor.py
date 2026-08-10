"""LLM-backed job-description extraction.

Same contract and safety rules as the resume LLM extractor: activates only with
a real API key, validates against the schema, retries once, and raises so the
selector can fall back to the deterministic extractor.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.schemas.jd_structured import JD_SCHEMA_VERSION, JDStructuredData
from app.services.ai.factory import AIFactory
from app.services.parsing.line_utils import dedupe_preserving_order
from app.services.parsing.skill_vocabulary import normalize_skill

logger = logging.getLogger(__name__)

MAX_INPUT_CHARS = 12000

_JSON_FENCE = re.compile(r"```(?:json)?\s*(?P<body>.+?)```", re.DOTALL | re.IGNORECASE)

_SYSTEM_PROMPT = """You are a precise job-description parser. You convert postings into JSON.

Rules:
- Return ONLY a JSON object. No prose, no markdown fences, no explanation.
- Copy values verbatim from the posting. Never invent or infer requirements.
- Use null for a missing scalar and [] for a missing list.
- mandatory_skills are stated requirements. preferred_skills are the ones
  described as nice to have, preferred, desirable, or a bonus.
- Never treat a word from the job title or company boilerplate as a skill."""

_SCHEMA_BLOCK = """{
  "role": str|null,
  "company": str|null,
  "location": str|null,
  "work_mode": "remote"|"hybrid"|"onsite"|null,
  "employment_type": str|null,
  "seniority": "intern"|"entry"|"mid"|"senior"|"staff"|"principal"|"lead"|null,
  "min_experience_years": int|null,
  "max_experience_years": int|null,
  "requirements": {
    "mandatory_skills": [str],
    "preferred_skills": [str],
    "qualifications": [str]
  },
  "responsibilities": [str]
}"""


class LLMJDExtractionError(RuntimeError):
    """Raised when the model cannot produce a valid structured JD."""


class LLMJDExtractor:
    name = "llm"

    def __init__(self, provider=None):
        self._provider = provider

    @staticmethod
    def is_available() -> bool:
        return AIFactory.is_available()

    async def extract(self, text: str) -> JDStructuredData:
        if not (text or "").strip():
            raise LLMJDExtractionError("Cannot extract structure from empty text")

        provider = self._provider or AIFactory.get_provider()
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": self._build_prompt(text)},
        ]

        raw = await provider.chat_completion(messages, temperature=0.0)
        payload = self._parse_json(raw)

        if payload is None:
            raw = await provider.chat_completion(
                messages + [
                    {"role": "assistant", "content": raw or ""},
                    {"role": "user", "content": "That was not valid JSON. Return the JSON object only."},
                ],
                temperature=0.0,
            )
            payload = self._parse_json(raw)

        if payload is None:
            raise LLMJDExtractionError("Model did not return parseable JSON")

        return self._build_result(payload)

    def _build_prompt(self, text: str) -> str:
        body = text[:MAX_INPUT_CHARS]
        truncated = "\n[TRUNCATED]" if len(text) > MAX_INPUT_CHARS else ""
        return (
            f"Extract this job description into exactly this JSON shape:\n{_SCHEMA_BLOCK}\n\n"
            f"JOB DESCRIPTION:\n{body}{truncated}"
        )

    def _parse_json(self, raw: Optional[str]) -> Optional[Dict[str, Any]]:
        if not raw:
            return None

        fenced = _JSON_FENCE.search(raw)
        candidates = [fenced.group("body")] if fenced else []

        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end > start:
            candidates.append(raw[start:end + 1])

        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(parsed, dict):
                return parsed

        return None

    def _build_result(self, payload: Dict[str, Any]) -> JDStructuredData:
        payload.pop("schema_version", None)
        payload.pop("keywords", None)
        payload.pop("extraction_meta", None)

        try:
            data = JDStructuredData(schema_version=JD_SCHEMA_VERSION, **payload)
        except Exception as exc:  # noqa: BLE001 - pydantic raises many shapes
            raise LLMJDExtractionError(f"Model output failed schema validation: {exc}") from exc

        # A required skill stays required even if the model repeats it as a
        # nice-to-have.
        mandatory = dedupe_preserving_order(data.requirements.mandatory_skills)
        preferred = [
            skill for skill in dedupe_preserving_order(data.requirements.preferred_skills)
            if skill not in mandatory
        ]

        data.requirements.mandatory_skills = mandatory
        data.requirements.preferred_skills = preferred
        data.requirements.normalized_mandatory = self._normalize(mandatory)
        data.requirements.normalized_preferred = self._normalize(preferred)
        data.keywords = dedupe_preserving_order(mandatory + preferred)
        data.extraction_meta = {
            "extractor": self.name,
            "confidence": self._confidence(data),
        }
        return data

    def _normalize(self, skills: List[str]) -> List[str]:
        return dedupe_preserving_order([normalize_skill(skill).lower() for skill in skills])

    def _confidence(self, data: JDStructuredData) -> float:
        signals = [
            bool(data.role),
            bool(data.company),
            bool(data.requirements.mandatory_skills),
            bool(data.responsibilities),
            data.min_experience_years is not None,
            bool(data.seniority),
            bool(data.requirements.qualifications or data.requirements.preferred_skills),
        ]
        return round(sum(signals) / len(signals), 3)
