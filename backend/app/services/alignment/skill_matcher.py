"""Weighted skill matching between a resume and a job description.

Replaces plain set intersection, which treated every requirement as equally
important and had no notion of "close but not exact". Three ideas drive it:

- A skill named in the job title, or repeated through the posting, matters more
  than one mentioned once.
- Preferred skills are a bonus. Missing them must never reduce the score.
- Covering a requirement's area with a different tool (Docker where the JD asks
  for Kubernetes) is worth partial credit, not zero.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from app.services.parsing.skill_vocabulary import (
    category_of,
    normalize_skill,
    supports_partial_credit,
)

BASE_WEIGHT = 1.0
TITLE_BONUS = 0.5        # named in the job title
FREQUENCY_BONUS = 0.25   # repeated through the posting
FREQUENT_MENTIONS = 3

PARTIAL_CREDIT = 0.4

# Preferred skills can only add. Full coverage of them is worth this many
# points on top of the mandatory score.
PREFERRED_BONUS_POINTS = 5.0


@dataclass
class SkillRequirement:
    skill: str                     # canonical display name
    normalized: str
    weight: float
    importance: str                # "mandatory" | "preferred"
    category: Optional[str] = None
    credit: float = 0.0            # 0.0 missing, PARTIAL_CREDIT partial, 1.0 matched
    covered_by: Optional[str] = None

    @property
    def priority(self) -> str:
        """P1 critical, P2 important, P3 bonus - per docs/skill-gap-engine.md."""
        if self.importance == "preferred":
            return "P3"
        return "P1" if self.weight > BASE_WEIGHT else "P2"


@dataclass
class SkillMatchReport:
    score: float = 0.0                              # 0-100
    matched: List[str] = field(default_factory=list)
    partial: List[SkillRequirement] = field(default_factory=list)
    missing: List[SkillRequirement] = field(default_factory=list)
    mandatory_coverage: float = 0.0
    preferred_coverage: float = 0.0
    has_requirements: bool = False

    @property
    def missing_display_names(self) -> List[str]:
        return [item.skill for item in self.missing]


class SkillMatcher:
    def match(self, resume_data: Dict[str, Any], jd_data: Dict[str, Any]) -> SkillMatchReport:
        resume_skills = self._resume_skills(resume_data)
        resume_categories = self._categories(resume_skills)

        mandatory = self._requirements(jd_data, "mandatory")
        preferred = self._requirements(jd_data, "preferred")

        if not mandatory and not preferred:
            return SkillMatchReport()

        self._apply_weights(mandatory, jd_data)
        for requirement in mandatory + preferred:
            self._score_requirement(requirement, resume_skills, resume_categories)

        mandatory_coverage = self._coverage(mandatory)
        preferred_coverage = self._coverage(preferred)

        # Preferred skills add, never subtract.
        bonus = (preferred_coverage / 100.0) * PREFERRED_BONUS_POINTS if preferred else 0.0
        score = mandatory_coverage if mandatory else preferred_coverage
        score = min(100.0, score + bonus) if mandatory else score

        everything = mandatory + preferred
        return SkillMatchReport(
            score=round(score, 2),
            matched=[item.skill for item in everything if item.credit >= 1.0],
            partial=[item for item in everything if 0.0 < item.credit < 1.0],
            missing=self._rank([item for item in everything if item.credit <= 0.0]),
            mandatory_coverage=round(mandatory_coverage, 2),
            preferred_coverage=round(preferred_coverage, 2),
            has_requirements=True,
        )

    # ---------------------------------------------------------------- internals

    def _resume_skills(self, resume_data: Dict[str, Any]) -> Set[str]:
        skills = resume_data.get("skills", {}) or {}
        source = skills.get("normalized") or skills.get("hard_skills") or []
        return {str(skill).strip().lower() for skill in source if str(skill).strip()}

    def _categories(self, normalized_skills: Set[str]) -> Dict[str, str]:
        """Category -> the resume skill that covers it."""
        covered: Dict[str, str] = {}
        for skill in normalized_skills:
            category = category_of(skill)
            if category and category not in covered:
                covered[category] = skill
        return covered

    def _requirements(self, jd_data: Dict[str, Any], importance: str) -> List[SkillRequirement]:
        requirements = jd_data.get("requirements", {}) or {}
        display = requirements.get(f"{importance}_skills")
        if display is None and importance == "mandatory":
            display = requirements.get("mandatory")  # pre-Phase-3 payloads
        normalized = requirements.get(f"normalized_{importance}") or []

        items: List[SkillRequirement] = []
        seen: Set[str] = set()

        for index, name in enumerate(display or []):
            label = str(name).strip()
            if not label:
                continue
            key = (
                str(normalized[index]).lower()
                if index < len(normalized) and normalized[index]
                else normalize_skill(label).lower()
            )
            if key in seen:
                continue
            seen.add(key)
            items.append(SkillRequirement(
                skill=label,
                normalized=key,
                weight=BASE_WEIGHT if importance == "mandatory" else 0.25,
                importance=importance,
                category=category_of(label),
            ))

        return items

    def _apply_weights(self, requirements: List[SkillRequirement], jd_data: Dict[str, Any]) -> None:
        title = (jd_data.get("role") or "").lower()
        haystack = self._weighting_text(jd_data).lower()

        for requirement in requirements:
            if requirement.normalized and requirement.normalized in title:
                requirement.weight += TITLE_BONUS
            elif self._mentions(haystack, requirement.normalized) >= FREQUENT_MENTIONS:
                requirement.weight += FREQUENCY_BONUS

    def _weighting_text(self, jd_data: Dict[str, Any]) -> str:
        """Text used to judge how often a requirement is emphasised."""
        parts: List[str] = [jd_data.get("role") or ""]
        parts.extend(jd_data.get("responsibilities") or [])
        requirements = jd_data.get("requirements", {}) or {}
        parts.extend(requirements.get("qualifications") or [])
        parts.extend(requirements.get("mandatory_skills") or [])
        parts.extend(requirements.get("preferred_skills") or [])
        return "\n".join(str(part) for part in parts)

    def _mentions(self, haystack: str, needle: str) -> int:
        if not needle:
            return 0
        return len(re.findall(rf"(?<![\w+#]){re.escape(needle)}(?![\w+#])", haystack))

    def _score_requirement(
        self,
        requirement: SkillRequirement,
        resume_skills: Set[str],
        resume_categories: Dict[str, str],
    ) -> None:
        if requirement.normalized in resume_skills:
            requirement.credit = 1.0
            requirement.covered_by = requirement.skill
            return

        if supports_partial_credit(requirement.category):
            covering = resume_categories.get(requirement.category or "")
            if covering:
                requirement.credit = PARTIAL_CREDIT
                # Resume skills are stored lowercase; show the canonical name.
                requirement.covered_by = normalize_skill(covering)

    def _coverage(self, requirements: List[SkillRequirement]) -> float:
        total = sum(item.weight for item in requirements)
        if total <= 0:
            return 0.0
        earned = sum(item.weight * item.credit for item in requirements)
        return (earned / total) * 100.0

    def _rank(self, missing: List[SkillRequirement]) -> List[SkillRequirement]:
        order = {"P1": 0, "P2": 1, "P3": 2}
        return sorted(missing, key=lambda item: (order[item.priority], -item.weight, item.skill))
