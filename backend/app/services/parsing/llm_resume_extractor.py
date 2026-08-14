"""LLM-backed resume extraction.

Activates only when the configured provider has a usable API key. Output is
validated against `ResumeStructuredData`; on invalid JSON the model gets one
repair attempt, and anything still broken raises so the selector can fall back
to the heuristic extractor.
"""

import json
import logging
import re
from typing import Any, Dict, Optional

from app.schemas.structured import SCHEMA_VERSION, ExperienceEntry, ResumeStructuredData
from app.services.ai.factory import AIFactory
from app.services.parsing.date_utils import DateRange, parse_single_date, total_years
from app.services.parsing.line_utils import dedupe_preserving_order
from app.services.parsing.skill_vocabulary import find_skills, normalize_skill

logger = logging.getLogger(__name__)

# Long resumes are truncated; the tail of a resume is rarely load-bearing and
# free-tier context windows are finite.
MAX_INPUT_CHARS = 12000

_JSON_FENCE = re.compile(r"```(?:json)?\s*(?P<body>.+?)```", re.DOTALL | re.IGNORECASE)

_SYSTEM_PROMPT = """You are a precise resume parser. You convert resume text into JSON.

Rules:
- Return ONLY a JSON object. No prose, no markdown fences, no explanation.
- Copy values verbatim from the resume. Never invent, infer, or embellish.
- Use null for a missing scalar and [] for a missing list.
- Dates use "YYYY-MM". An ongoing role uses "present" as end_date.
- highlights are the bullet points of that entry, each as a full sentence."""

_SCHEMA_BLOCK = """{
  "personal_info": {
    "name": str|null, "title": str|null, "email": str|null,
    "phone": str|null, "location": str|null,
    "links": {"linkedin": str|null, "github": str|null, "portfolio": str|null, "other": [str]}
  },
  "summary": str|null,
  "skills": {
    "hard_skills": [str],
    "soft_skills": [str],
    "categories": {"<category name>": [str]}
  },
  "experience": [{
    "company": str|null, "role": str|null, "location": str|null,
    "start_date": "YYYY-MM"|null, "end_date": "YYYY-MM"|"present"|null,
    "is_internship": bool, "highlights": [str]
  }],
  "education": [{
    "degree": str|null, "institution": str|null, "location": str|null,
    "start_year": int|null, "end_year": int|null, "score": str|null, "highlights": [str]
  }],
  "projects": [{
    "name": str|null, "description": str|null, "tech_stack": [str],
    "links": [str], "start_date": str|null, "end_date": str|null, "highlights": [str]
  }],
  "certifications": [{"name": str|null, "issuer": str|null, "year": int|null}],
  "achievements": [str]
}"""


class LLMExtractionError(RuntimeError):
    """Raised when the model cannot produce a valid structured resume."""


class LLMResumeExtractor:
    """Few-shot JSON extraction with schema validation and one repair retry."""

    name = "llm"

    def __init__(self, provider=None):
        # Injectable so tests can drive it without network access.
        self._provider = provider

    @staticmethod
    def is_available() -> bool:
        return AIFactory.is_available()

    async def extract(self, text: str) -> ResumeStructuredData:
        if not (text or "").strip():
            raise LLMExtractionError("Cannot extract structure from empty text")

        provider = self._provider or AIFactory.get_provider()
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": self._build_prompt(text)},
        ]

        raw = await provider.chat_completion(messages, temperature=0.0, json_mode=True)
        payload = self._parse_json(raw)

        if payload is None:
            raw = await provider.chat_completion(
                messages + [
                    {"role": "assistant", "content": raw or ""},
                    {"role": "user", "content": "That was not valid JSON. Return the JSON object only."},
                ],
                temperature=0.0,
                json_mode=True,
            )
            payload = self._parse_json(raw)

        if payload is None:
            raise LLMExtractionError("Model did not return parseable JSON")

        return self._build_result(payload, text)

    def _build_prompt(self, text: str) -> str:
        body = text[:MAX_INPUT_CHARS]
        truncated = "\n[TRUNCATED]" if len(text) > MAX_INPUT_CHARS else ""
        return (
            f"Extract this resume into exactly this JSON shape:\n{_SCHEMA_BLOCK}\n\n"
            f"RESUME TEXT:\n{body}{truncated}"
        )

    def _parse_json(self, raw: Optional[str]) -> Optional[Dict[str, Any]]:
        """Recover a JSON object from a model response.

        Models wrap JSON in prose or fences despite instructions, so the fenced
        block is tried first, then the outermost braces.
        """
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

    def _build_result(self, payload: Dict[str, Any], text: str) -> ResumeStructuredData:
        payload.pop("schema_version", None)
        payload.pop("total_experience_years", None)
        payload.pop("extraction_meta", None)

        try:
            data = ResumeStructuredData(schema_version=SCHEMA_VERSION, **payload)
        except Exception as exc:  # noqa: BLE001 - pydantic raises many shapes
            raise LLMExtractionError(f"Model output failed schema validation: {exc}") from exc

        # Durations and totals are arithmetic, not judgement: compute them from
        # the model's dates rather than trusting it to add up months.
        data.total_experience_years = self._compute_experience_years(data)
        for entry in data.experience:
            entry.duration_months = self._entry_months(entry)
            entry.is_current = (entry.end_date or "").lower() == "present"

        data.skills.hard_skills = self._merge_skills(data, text)
        data.skills.normalized = self._normalize(data.skills.hard_skills)
        data.extraction_meta = {
            "extractor": self.name,
            "confidence": self._confidence(data),
        }
        return data

    def _merge_skills(self, data: ResumeStructuredData, text: str) -> list:
        listed = list(data.skills.hard_skills)
        for items in data.skills.categories.values():
            listed.extend(items)
        return dedupe_preserving_order(listed + find_skills(text))

    def _normalize(self, skills: list) -> list:
        return dedupe_preserving_order([normalize_skill(skill).lower() for skill in skills])

    def _compute_experience_years(self, data: ResumeStructuredData) -> float:
        ranges = []
        for entry in data.experience:
            start = parse_single_date(entry.start_date or "")
            if start is None:
                continue
            is_current = (entry.end_date or "").lower() == "present"
            end = None if is_current else parse_single_date(entry.end_date or "")
            ranges.append(DateRange(start=start, end=end, is_current=is_current))

        return total_years(ranges)

    def _entry_months(self, entry: ExperienceEntry) -> Optional[int]:
        start = parse_single_date(entry.start_date or "")
        if start is None:
            return None
        is_current = (entry.end_date or "").lower() == "present"
        end = None if is_current else parse_single_date(entry.end_date or "")
        return DateRange(start=start, end=end, is_current=is_current).duration_months

    def _confidence(self, data: ResumeStructuredData) -> float:
        signals = [
            bool(data.personal_info.name),
            bool(data.personal_info.email),
            bool(data.skills.hard_skills),
            bool(data.experience),
            bool(data.education),
            bool(data.summary or data.projects),
            any(entry.start_date for entry in data.experience) or bool(data.education),
            all(entry.role or entry.company for entry in data.experience) if data.experience else False,
        ]
        return round(sum(signals) / len(signals), 3)
