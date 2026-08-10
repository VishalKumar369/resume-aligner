"""Put the JD-relevant material first.

Screeners and parsers both weight what they read first. Reordering changes
nothing factual, so it is the safest optimization available.

Employment history order is deliberately left alone - resequencing jobs would
misrepresent a career. Only bullets *within* a role, the skills list, and the
projects list are reordered.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Set

from app.services.parsing.skill_vocabulary import find_skills, normalize_skill


@dataclass
class ReorderResult:
    changes: List[str] = field(default_factory=list)


class Reorderer:
    def apply(self, resume_data: Dict[str, Any], jd_data: Dict[str, Any]) -> ReorderResult:
        """Reorder `resume_data` in place and report what moved."""
        wanted = self._jd_skills(jd_data)
        result = ReorderResult()

        if not wanted:
            return result

        self._reorder_skills(resume_data, wanted, result)
        self._reorder_highlights(resume_data, wanted, result)
        self._reorder_projects(resume_data, wanted, result)
        return result

    # ---------------------------------------------------------------- internals

    def _jd_skills(self, jd_data: Dict[str, Any]) -> Set[str]:
        requirements = jd_data.get("requirements", {}) or {}
        wanted = list(requirements.get("normalized_mandatory") or [])
        wanted += list(requirements.get("normalized_preferred") or [])
        return {str(skill).strip().lower() for skill in wanted if str(skill).strip()}

    def _reorder_skills(
        self, resume_data: Dict[str, Any], wanted: Set[str], result: ReorderResult
    ) -> None:
        skills = resume_data.get("skills")
        if not isinstance(skills, dict):
            return

        original = list(skills.get("hard_skills") or [])
        reordered = self._relevant_first(original, lambda item: self._is_wanted(item, wanted))
        if reordered != original:
            skills["hard_skills"] = reordered
            result.changes.append("Moved the job's required skills to the front of your skills list.")

        categories = skills.get("categories")
        if isinstance(categories, dict):
            for name, items in categories.items():
                if not isinstance(items, list):
                    continue
                categories[name] = self._relevant_first(
                    items, lambda item: self._is_wanted(item, wanted)
                )

    def _reorder_highlights(
        self, resume_data: Dict[str, Any], wanted: Set[str], result: ReorderResult
    ) -> None:
        moved = 0
        for entry in resume_data.get("experience") or []:
            if not isinstance(entry, dict):
                continue
            highlights = entry.get("highlights")
            if not isinstance(highlights, list) or len(highlights) < 2:
                continue

            reordered = self._relevant_first(
                highlights, lambda item: bool(self._skills_in(item) & wanted)
            )
            if reordered != highlights:
                entry["highlights"] = reordered
                moved += 1

        if moved:
            result.changes.append(
                f"Led with the most role-relevant bullet in {moved} experience "
                f"{'entry' if moved == 1 else 'entries'}."
            )

    def _reorder_projects(
        self, resume_data: Dict[str, Any], wanted: Set[str], result: ReorderResult
    ) -> None:
        projects = resume_data.get("projects")
        if not isinstance(projects, list) or len(projects) < 2:
            return

        original = list(projects)
        ranked = sorted(
            enumerate(projects),
            key=lambda pair: (-self._project_relevance(pair[1], wanted), pair[0]),
        )
        reordered = [project for _, project in ranked]

        if reordered != original:
            resume_data["projects"] = reordered
            result.changes.append("Reordered projects so the most relevant one appears first.")

    def _project_relevance(self, project: Any, wanted: Set[str]) -> int:
        if not isinstance(project, dict):
            return 0
        text = " ".join([
            str(project.get("name") or ""),
            str(project.get("description") or ""),
            " ".join(str(item) for item in project.get("tech_stack") or []),
            " ".join(str(item) for item in project.get("highlights") or []),
        ])
        return len(self._skills_in(text) & wanted)

    def _relevant_first(self, items: List[Any], is_relevant) -> List[Any]:
        """Stable partition: relevant items first, original order preserved."""
        relevant = [item for item in items if is_relevant(item)]
        rest = [item for item in items if not is_relevant(item)]
        return relevant + rest

    def _is_wanted(self, skill: Any, wanted: Set[str]) -> bool:
        return normalize_skill(str(skill)).lower() in wanted

    def _skills_in(self, text: Any) -> Set[str]:
        return {skill.lower() for skill in find_skills(str(text))}
