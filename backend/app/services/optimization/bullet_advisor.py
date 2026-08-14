"""Per-bullet advice for anything the optimizer did not rewrite.

A rule cannot rephrase prose, but it can say precisely what is wrong with a
bullet and which of the role's language it is missing. That advice is useful on
its own, and it is the whole deliverable when no LLM is configured.
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Set

from app.schemas.structured import entries
from app.services.ats.ats_engine import (
    ACTION_VERBS,
    MAX_BULLET_WORDS,
    METRIC_PATTERN,
    MIN_BULLET_WORDS,
)
from app.services.parsing.skill_vocabulary import find_skills

MAX_SUGGESTIONS = 8

_WORD = re.compile(r"[a-z][a-z0-9+#./-]{3,}")

_STOPWORDS = frozenset("""
and or the for from with within into onto over under across about above below
between during that this these those will would can could should may might must
your their our its work working works role team job position company using use
used other more most such via per including include includes strong good great
excellent ability able experience experienced years year end also well etc
design designing build building
""".split())


@dataclass
class BulletAdvice:
    company: str
    bullet: str
    issues: List[str]

    def as_sentence(self) -> str:
        where = f" ({self.company})" if self.company else ""
        return f"{self.bullet[:70]}...{where}: {'; '.join(self.issues)}"


class BulletAdvisor:
    def advise(
        self,
        resume_data: Dict[str, Any],
        jd_data: Dict[str, Any],
        skip: Set[str] = frozenset(),
    ) -> List[str]:
        """Suggestions for bullets, ignoring any already rewritten."""
        jd_terms = self._jd_terms(jd_data)
        suggestions: List[str] = []

        for entry in entries(resume_data, "experience"):
            company = str(entry.get("company") or "")
            for bullet in entry.get("highlights") or []:
                text = str(bullet).strip()
                if not text or text in skip:
                    continue

                issues = self._issues(text, jd_terms)
                if issues:
                    suggestions.append(BulletAdvice(company, text, issues).as_sentence())

        return suggestions[:MAX_SUGGESTIONS]

    # ---------------------------------------------------------------- internals

    def _issues(self, bullet: str, jd_terms: Set[str]) -> List[str]:
        issues: List[str] = []
        words = bullet.split()

        if not METRIC_PATTERN.search(bullet):
            issues.append("add a number to show scale or impact")

        first = re.sub(r"[^a-z]", "", words[0].lower()) if words else ""
        if first and first not in ACTION_VERBS:
            issues.append(f"start with an action verb instead of '{words[0]}'")

        if len(words) > MAX_BULLET_WORDS:
            issues.append("shorten to a single line")
        elif len(words) < MIN_BULLET_WORDS:
            issues.append("expand with what you actually did")

        missing = self._missing_terms(bullet, jd_terms)
        if missing:
            issues.append(f"mirror the job's language: {', '.join(missing)}")

        return issues

    def _missing_terms(self, bullet: str, jd_terms: Set[str]) -> List[str]:
        """Role vocabulary related to this bullet but absent from it."""
        bullet_skills = {skill.lower() for skill in find_skills(bullet)}
        if not bullet_skills:
            return []

        present = self._terms(bullet)
        return sorted(jd_terms - present)[:3]

    def _jd_terms(self, jd_data: Dict[str, Any]) -> Set[str]:
        chunks = list(jd_data.get("responsibilities") or [])
        requirements = jd_data.get("requirements", {}) or {}
        chunks.extend(requirements.get("mandatory_skills") or [])
        return self._terms(" ".join(str(chunk) for chunk in chunks))

    def _terms(self, text: str) -> Set[str]:
        return {
            word for word in _WORD.findall(str(text).lower())
            if word not in _STOPWORDS
        }
