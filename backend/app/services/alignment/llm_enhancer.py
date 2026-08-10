"""Optional LLM layer over the deterministic alignment score.

Responsibility overlap is the one component a keyword method approximates
badly: "owned the payments platform" and "led billing services end to end" are
the same claim in different words. When an API key is configured, a model
scores that similarity and writes the feedback prose.

It can only influence the responsibility component and the wording of the
advice. Skills, seniority, projects, and the ATS score stay deterministic, so
a model outage cannot move the headline numbers around.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.services.ai.factory import AIFactory

logger = logging.getLogger(__name__)

MAX_ITEMS = 12

_SYSTEM_PROMPT = """You assess how well a candidate's experience matches a role's
responsibilities. You are strict and evidence-based.

Rules:
- Return ONLY a JSON object. No prose, no markdown fences.
- responsibility_match is 0-100: how much of the role's day-to-day work the
  candidate has demonstrably done before. Judge substance, not wording.
- Never invent experience the resume does not state.
- Each suggestion must be one specific, actionable sentence."""

_SCHEMA_BLOCK = """{
  "responsibility_match": int,
  "feedback": str,
  "improvement_suggestions": [str]
}"""


class LLMAlignmentEnhancer:
    name = "llm"

    def __init__(self, provider=None):
        self._provider = provider

    @staticmethod
    def is_available() -> bool:
        return AIFactory.is_available()

    async def enhance(
        self, resume_data: Dict[str, Any], jd_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Return the model's assessment, or None if it produced nothing usable."""
        responsibilities = jd_data.get("responsibilities") or []
        evidence = self._resume_evidence(resume_data)
        if not responsibilities or not evidence:
            return None

        provider = self._provider or AIFactory.get_provider()
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": self._build_prompt(responsibilities, evidence, jd_data)},
        ]

        raw = await provider.chat_completion(messages, temperature=0.0)
        payload = self._parse_json(raw)
        if payload is None:
            return None

        return self._clean(payload)

    # ---------------------------------------------------------------- internals

    def _build_prompt(
        self, responsibilities: List[str], evidence: List[str], jd_data: Dict[str, Any]
    ) -> str:
        role = jd_data.get("role") or "the role"
        listed = "\n".join(f"- {item}" for item in responsibilities[:MAX_ITEMS])
        done = "\n".join(f"- {item}" for item in evidence[:MAX_ITEMS])
        return (
            f"Return exactly this JSON shape:\n{_SCHEMA_BLOCK}\n\n"
            f"ROLE: {role}\n\nRESPONSIBILITIES:\n{listed}\n\n"
            f"WHAT THE CANDIDATE HAS DONE:\n{done}"
        )

    def _resume_evidence(self, resume_data: Dict[str, Any]) -> List[str]:
        evidence: List[str] = []
        for entry in resume_data.get("experience") or []:
            role = entry.get("role")
            for highlight in entry.get("highlights") or []:
                evidence.append(f"{role}: {highlight}" if role else str(highlight))
        return evidence

    def _parse_json(self, raw: Optional[str]) -> Optional[Dict[str, Any]]:
        if not raw:
            return None

        fenced = re.search(r"```(?:json)?\s*(.+?)```", raw, re.DOTALL | re.IGNORECASE)
        candidates = [fenced.group(1)] if fenced else []

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

    def _clean(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            score = float(payload.get("responsibility_match"))
        except (TypeError, ValueError):
            return None

        if not 0.0 <= score <= 100.0:
            return None

        suggestions = [
            str(item).strip()
            for item in (payload.get("improvement_suggestions") or [])
            if str(item).strip()
        ]
        feedback = str(payload.get("feedback") or "").strip()

        return {
            "responsibility_match": round(score, 2),
            "feedback": feedback or None,
            "improvement_suggestions": suggestions[:MAX_ITEMS],
        }
