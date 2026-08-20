"""Condense a resume so it fits on a single page.

When single page is chosen, single page is guaranteed. The rule is quantity
down, JD-relevance up: content is removed weakest-first, so keyword-bearing,
job-relevant material is the last thing to go, but the page target always wins
over bullet counts.

Removal escalates gently → aggressively, re-measuring the real PDF render after
every cut and stopping the instant it fits:

  1. trim the weakest bullets, keeping a comfortable floor per entry
  2. drop projects / achievements that carry no JD relevance at all
  3. trim bullets down to one per entry
  4. drop remaining projects (least relevant first) - they are supplementary
     to work history and education
  5. drop the summary paragraph

Work-experience roles always keep at least one bullet and no section header is
touched, so the document still reads as a real resume.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from app.services.documents.writers import count_pdf_pages
from app.services.parsing.skill_vocabulary import find_skills

# The floor the trim *starts* at - a comfortable number of bullets per entry.
# It is lowered automatically (down to one) when a single page demands it.
DEFAULT_MIN_BULLETS_PER_ROLE = 3

# Bullets are never cut below this for a work role: a job with no bullets reads
# as an error. Projects can be dropped whole instead.
HARD_FLOOR = 1

# Backstop so a pathological input cannot loop forever.
_MAX_REMOVALS = 400


@dataclass
class CondenseResult:
    removed_bullets: int = 0
    dropped_projects: int = 0
    dropped_achievements: int = 0
    removed_summary: bool = False
    fits: bool = True
    page_count: int = 1
    changes: List[Dict[str, str]] = field(default_factory=list)

    @property
    def total_removed(self) -> int:
        return (
            self.removed_bullets
            + self.dropped_projects
            + self.dropped_achievements
            + (1 if self.removed_summary else 0)
        )


class SinglePageCondenser:
    def __init__(
        self,
        min_bullets_per_role: int = DEFAULT_MIN_BULLETS_PER_ROLE,
        page_counter=None,
    ):
        self.min_bullets_per_role = max(HARD_FLOOR, min_bullets_per_role)
        # Injectable so tests can drive the escalation without rendering a PDF.
        self._page_counter = page_counter or count_pdf_pages

    def condense(
        self,
        resume_data: Dict[str, Any],
        jd_data: Dict[str, Any],
        target_pages: int = 1,
    ) -> CondenseResult:
        """Trim `resume_data` in place until it fits `target_pages`."""
        pages = self._page_counter(resume_data)
        result = CondenseResult(page_count=pages, fits=pages <= target_pages)
        if result.fits:
            return result

        wanted = self._jd_skills(jd_data)

        # Strategies in gentle → aggressive order. Each performs at most one
        # removal and returns True while it still has something to remove. We
        # exhaust each before moving to the next, re-measuring after every cut.
        strategies = [
            lambda: self._trim_weakest_bullet(resume_data, wanted, self.min_bullets_per_role, result),
            lambda: self._drop_irrelevant_project(resume_data, wanted, result, only_zero=True),
            lambda: self._drop_irrelevant_achievement(resume_data, wanted, result),
            lambda: self._trim_weakest_bullet(resume_data, wanted, HARD_FLOOR, result),
            lambda: self._drop_irrelevant_project(resume_data, wanted, result, only_zero=False),
            lambda: self._remove_summary(resume_data, result),
        ]

        index = 0
        while pages > target_pages and result.total_removed < _MAX_REMOVALS:
            if index >= len(strategies):
                break  # every lever pulled; the note will be honest about it
            if strategies[index]():
                pages = self._page_counter(resume_data)
            else:
                index += 1  # this lever is exhausted, escalate

        result.page_count = pages
        result.fits = pages <= target_pages
        self._summarize(result)
        return result

    # ------------------------------------------------------------- strategies

    def _trim_weakest_bullet(
        self, data: Dict[str, Any], wanted: Set[str], floor: int, result: CondenseResult
    ) -> bool:
        """Drop the single least-valuable bullet from any entry above `floor`."""
        location = self._weakest_removable_bullet(data, wanted, floor)
        if location is None:
            return False
        entries, entry_index, bullet_index = location
        del entries[entry_index]["highlights"][bullet_index]
        result.removed_bullets += 1
        return True

    def _drop_irrelevant_project(
        self, data: Dict[str, Any], wanted: Set[str], result: CondenseResult, only_zero: bool
    ) -> bool:
        """Remove one project. With `only_zero`, only a project with no JD
        relevance at all; otherwise the least-relevant remaining project."""
        projects = data.get("projects")
        if not isinstance(projects, list) or not projects:
            return False

        ranked = sorted(
            range(len(projects)),
            key=lambda i: (self._project_relevance(projects[i], wanted), i),
        )
        target = ranked[0]
        if only_zero and self._project_relevance(projects[target], wanted) > 0:
            return False

        del projects[target]
        result.dropped_projects += 1
        return True

    def _drop_irrelevant_achievement(
        self, data: Dict[str, Any], wanted: Set[str], result: CondenseResult
    ) -> bool:
        achievements = data.get("achievements")
        if not isinstance(achievements, list) or not achievements:
            return False

        for i, item in enumerate(achievements):
            if not self._skills_in(str(item)) & wanted:
                del achievements[i]
                result.dropped_achievements += 1
                return True
        return False

    def _remove_summary(self, data: Dict[str, Any], result: CondenseResult) -> bool:
        if str(data.get("summary") or "").strip():
            data["summary"] = ""
            result.removed_summary = True
            return True
        return False

    # ---------------------------------------------------------------- ranking

    def _weakest_removable_bullet(
        self, data: Dict[str, Any], wanted: Set[str], floor: int
    ) -> Optional[Tuple[List[Dict[str, Any]], int, int]]:
        """The best bullet to drop next, or None if every entry is at `floor`.

        "Best to drop" = fewest JD skills, then longest (frees the most space
        per cut), then latest in its entry (earlier bullets usually lead).
        """
        best: Optional[Tuple[List[Dict[str, Any]], int, int]] = None
        best_rank: Optional[Tuple[int, int, int]] = None

        for section in ("experience", "projects"):
            entries = data.get(section)
            if not isinstance(entries, list):
                continue

            for entry_index, entry in enumerate(entries):
                if not isinstance(entry, dict):
                    continue
                highlights = entry.get("highlights")
                if not isinstance(highlights, list) or len(highlights) <= floor:
                    continue

                for bullet_index, bullet in enumerate(highlights):
                    text = str(bullet)
                    relevance = len(self._skills_in(text) & wanted)
                    rank = (relevance, -len(text), -bullet_index)
                    if best_rank is None or rank < best_rank:
                        best_rank = rank
                        best = (entries, entry_index, bullet_index)

        return best

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

    def _jd_skills(self, jd_data: Dict[str, Any]) -> Set[str]:
        requirements = jd_data.get("requirements", {}) or {}
        wanted = list(requirements.get("normalized_mandatory") or [])
        wanted += list(requirements.get("normalized_preferred") or [])
        return {str(skill).strip().lower() for skill in wanted if str(skill).strip()}

    def _skills_in(self, text: str) -> Set[str]:
        return {skill.lower() for skill in find_skills(text)}

    # ------------------------------------------------------------------ report

    def _summarize(self, result: CondenseResult) -> None:
        if result.total_removed == 0:
            return

        cut: List[str] = []
        if result.removed_bullets:
            cut.append(
                f"{result.removed_bullets} lower-impact bullet"
                f"{'' if result.removed_bullets == 1 else 's'}"
            )
        if result.dropped_projects:
            cut.append(
                f"{result.dropped_projects} less-relevant project"
                f"{'' if result.dropped_projects == 1 else 's'}"
            )
        if result.dropped_achievements:
            cut.append(f"{result.dropped_achievements} achievement(s)")
        if result.removed_summary:
            cut.append("the summary")

        result.changes.append({
            "type": "condensed_single_page",
            "description": (
                "Condensed to a single page by trimming "
                + ", ".join(cut)
                + ". Skills, work history, education, and the most job-relevant "
                "content were kept."
            ),
        })
