"""LLM bullet rewriting, gated by the fact guard.

Every rewrite the model returns is diffed against its original before being
accepted. A rewrite that introduces a figure, technology, or name that was not
there is discarded and the original bullet is kept - see `fact_guard`.

All bullets go in a single request. Free-tier providers are rate limited per
minute, so one call for the whole resume is the difference between working and
not.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.schemas.structured import entries
from app.services.ai.factory import AIFactory
from app.services.optimization.fact_guard import FactGuard

logger = logging.getLogger(__name__)

# Cap the request so a long resume cannot blow the context or the rate limit.
MAX_BULLETS = 20

_JSON_FENCE = re.compile(r"```(?:json)?\s*(?P<body>.+?)```", re.DOTALL | re.IGNORECASE)

_SYSTEM_PROMPT = """You rewrite resume bullet points to mirror a job description's language.

Hard rules:
- Return ONLY a JSON object. No prose, no markdown fences.
- NEVER add a fact that is not in the original bullet. No new numbers,
  percentages, technologies, tools, employers, product names, or team sizes.
  Rewrites that add facts are rejected automatically.
- Keep the same claim. Change only the wording, structure, and emphasis.
- Start with a strong action verb. Keep it to one line.
- Reuse the job description's terminology where it genuinely describes the same
  work. If it does not, leave the bullet alone.
- If a bullet is already well written, return it unchanged."""


@dataclass
class BulletRewrite:
    entry_index: int       # index into resume_data["experience"]
    bullet_index: int      # index into that entry's "highlights"
    company: str
    original: str
    rewritten: str

    @property
    def location(self) -> str:
        return f"experience.{self.entry_index}.highlights.{self.bullet_index}"


@dataclass
class RewriteResult:
    accepted: List[BulletRewrite] = field(default_factory=list)
    rejected: List[Dict[str, str]] = field(default_factory=list)
    considered: int = 0

    @property
    def rewritten_originals(self) -> set:
        return {item.original for item in self.accepted}


class LLMBulletRewriter:
    name = "llm"

    def __init__(self, provider=None, guard: Optional[FactGuard] = None):
        self._provider = provider
        self.guard = guard or FactGuard()
        # The raw model response of the last call, so the engine can cache it.
        self.last_payload: Optional[Dict[str, Any]] = None

    @staticmethod
    def is_available() -> bool:
        return AIFactory.is_available("bullet_rewriting")

    def cache_fingerprint(self, resume_data: Dict[str, Any], jd_data: Dict[str, Any]) -> list:
        """Inputs that determine the rewrite, for cache keying."""
        bullets = [item.original for item in self._collect_bullets(resume_data)]
        requirements = jd_data.get("requirements", {}) or {}
        return [
            jd_data.get("role") or "",
            requirements.get("mandatory_skills") or [],
            jd_data.get("responsibilities") or [],
            bullets,
        ]

    def rebuild(self, payload: Dict[str, Any], resume_data: Dict[str, Any]) -> "RewriteResult":
        """Re-verify a cached model response against the current resume.

        The guard runs again rather than trusting a stored verdict, so a change
        to the rules applies to cached results too.
        """
        return self._verify(payload, self._collect_bullets(resume_data))

    async def rewrite(
        self, resume_data: Dict[str, Any], jd_data: Dict[str, Any]
    ) -> RewriteResult:
        candidates = self._collect_bullets(resume_data)
        if not candidates:
            return RewriteResult()

        provider = self._provider or AIFactory.get_provider()
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": self._build_prompt(candidates, jd_data)},
        ]

        raw = await provider.chat_completion(messages, temperature=0.2, json_mode=True)
        payload = self._parse_json(raw)
        if payload is None:
            logger.warning("Bullet rewriter returned unparseable output")
            return RewriteResult(considered=len(candidates))

        self.last_payload = payload
        return self._verify(payload, candidates)

    # ---------------------------------------------------------------- internals

    def _collect_bullets(self, resume_data: Dict[str, Any]) -> List[BulletRewrite]:
        collected: List[BulletRewrite] = []

        for entry_index, entry in enumerate(entries(resume_data, "experience")):
            company = str(entry.get("company") or "")
            for bullet_index, bullet in enumerate(entry.get("highlights") or []):
                text = str(bullet).strip()
                if not text:
                    continue
                collected.append(BulletRewrite(
                    entry_index=entry_index,
                    bullet_index=bullet_index,
                    company=company,
                    original=text,
                    rewritten="",
                ))
                if len(collected) >= MAX_BULLETS:
                    return collected

        return collected

    def _build_prompt(self, candidates: List[BulletRewrite], jd_data: Dict[str, Any]) -> str:
        role = jd_data.get("role") or "the role"
        requirements = jd_data.get("requirements", {}) or {}
        skills = ", ".join(str(item) for item in requirements.get("mandatory_skills") or [])
        responsibilities = "\n".join(
            f"- {item}" for item in (jd_data.get("responsibilities") or [])[:10]
        )
        bullets = "\n".join(
            f"{index}. {item.original}" for index, item in enumerate(candidates)
        )

        return (
            f'Return exactly: {{"rewrites": [{{"index": int, "rewritten": str}}]}}\n\n'
            f"TARGET ROLE: {role}\n"
            f"REQUIRED SKILLS: {skills}\n"
            f"RESPONSIBILITIES:\n{responsibilities}\n\n"
            f"BULLETS TO REWRITE:\n{bullets}"
        )

    def _parse_json(self, raw: Optional[str]) -> Optional[Dict[str, Any]]:
        if not raw:
            return None

        fenced = _JSON_FENCE.search(raw)
        options = [fenced.group("body")] if fenced else []
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end > start:
            options.append(raw[start:end + 1])

        for option in options:
            try:
                parsed = json.loads(option)
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(parsed, dict):
                return parsed

        return None

    def _verify(
        self, payload: Dict[str, Any], candidates: List[BulletRewrite]
    ) -> RewriteResult:
        result = RewriteResult(considered=len(candidates))

        for item in payload.get("rewrites") or []:
            if not isinstance(item, dict):
                continue

            index = item.get("index")
            rewritten = str(item.get("rewritten") or "").strip()
            if not isinstance(index, int) or not 0 <= index < len(candidates):
                continue

            candidate = candidates[index]
            if not rewritten or rewritten == candidate.original:
                continue

            verdict = self.guard.check(candidate.original, rewritten)
            if verdict.accepted:
                result.accepted.append(BulletRewrite(
                    entry_index=candidate.entry_index,
                    bullet_index=candidate.bullet_index,
                    company=candidate.company,
                    original=candidate.original,
                    rewritten=rewritten,
                ))
            else:
                # Kept for transparency: the user can see what was blocked.
                result.rejected.append({
                    "original": candidate.original,
                    "rejected_rewrite": rewritten,
                    "reason": verdict.reason,
                })
                logger.info("Rejected a bullet rewrite: %s", verdict.reason)

        return result
