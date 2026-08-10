"""Surface skills the candidate already demonstrates but never listed.

A resume often proves a skill in a bullet or a project tech stack while the
SKILLS block - the part a screener reads first - never names it. Promoting those
into the printed skills section is a real ATS gain with nothing invented.

Only skills that are (a) asked for by the JD and (b) already evidenced somewhere
in the resume are promoted. A skill the candidate does not have is never added;
it stays a gap in `missing_skills`.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Set

from app.schemas.structured import entries
from app.services.parsing.line_utils import dedupe_preserving_order
from app.services.parsing.skill_vocabulary import find_skills, normalize_skill

PROMOTED_CATEGORY = "Additional Skills"


@dataclass
class PromotionResult:
    categories: Dict[str, List[str]] = field(default_factory=dict)
    hard_skills: List[str] = field(default_factory=list)
    # Recomputed alongside hard_skills so the two never drift; the scorer
    # matches on `normalized`.
    normalized: List[str] = field(default_factory=list)
    promoted: List[str] = field(default_factory=list)


class SkillPromoter:
    def promote(
        self, resume_data: Dict[str, Any], jd_data: Dict[str, Any]
    ) -> PromotionResult:
        skills = resume_data.get("skills", {}) or {}
        categories = {
            name: list(items)
            for name, items in (skills.get("categories") or {}).items()
        }
        hard_skills = list(skills.get("hard_skills") or [])

        wanted = self._jd_skills(jd_data)
        unchanged = PromotionResult(
            categories=categories,
            hard_skills=hard_skills,
            normalized=self._normalize(hard_skills),
        )
        if not wanted:
            return unchanged

        evidenced = self._evidenced_skills(resume_data)
        printed = self._printed_skills(categories, hard_skills)

        promoted = sorted(
            {normalize_skill(skill) for skill in (wanted & evidenced) - printed}
        )
        if not promoted:
            return unchanged

        categories[PROMOTED_CATEGORY] = dedupe_preserving_order(
            categories.get(PROMOTED_CATEGORY, []) + promoted
        )
        merged = dedupe_preserving_order(hard_skills + promoted)
        return PromotionResult(
            categories=categories,
            hard_skills=merged,
            normalized=self._normalize(merged),
            promoted=promoted,
        )

    def _normalize(self, skills: List[str]) -> List[str]:
        return dedupe_preserving_order(
            [normalize_skill(str(skill)).lower() for skill in skills if str(skill).strip()]
        )

    # ---------------------------------------------------------------- internals

    def _jd_skills(self, jd_data: Dict[str, Any]) -> Set[str]:
        requirements = jd_data.get("requirements", {}) or {}
        wanted = list(requirements.get("normalized_mandatory") or [])
        wanted += list(requirements.get("normalized_preferred") or [])
        return {str(skill).strip().lower() for skill in wanted if str(skill).strip()}

    def _evidenced_skills(self, resume_data: Dict[str, Any]) -> Set[str]:
        """Skills provable from the resume's own prose, not its skills list."""
        evidence: List[str] = [str(resume_data.get("summary") or "")]

        for entry in entries(resume_data, "experience"):
            evidence.append(str(entry.get("role") or ""))
            evidence.extend(str(item) for item in entry.get("highlights") or [])

        for entry in entries(resume_data, "projects"):
            evidence.append(str(entry.get("description") or ""))
            evidence.extend(str(item) for item in entry.get("tech_stack") or [])
            evidence.extend(str(item) for item in entry.get("highlights") or [])

        for entry in entries(resume_data, "certifications"):
            evidence.append(str(entry.get("name") or ""))

        evidence.extend(str(item) for item in resume_data.get("achievements") or [])

        return {skill.lower() for skill in find_skills("\n".join(evidence))}

    def _printed_skills(
        self, categories: Dict[str, List[str]], hard_skills: List[str]
    ) -> Set[str]:
        """Canonical forms of what the SKILLS section already names."""
        printed: List[str] = []
        for items in categories.values():
            printed.extend(items)
        if not categories:
            printed.extend(hard_skills)
        return {normalize_skill(str(skill)).lower() for skill in printed if str(skill).strip()}
