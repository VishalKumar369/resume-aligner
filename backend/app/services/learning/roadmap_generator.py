"""Turn aggregated skill gaps into an ordered, time-boxed learning plan.

Implements `docs/learning-roadmap-engine.md`: related gaps are clustered into one
module, modules are ordered by criticality and then by dependency, and each
carries an ETA and its official documentation.

Every skill in the plan comes from a real gap in a real job description the user
saved. Nothing is suggested speculatively.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.services.learning.resources import (
    module_name,
    prerequisite_of,
    resources_for,
)
from app.services.skill_gap.aggregator import AggregatedGap, GapReport, cluster_by_category

# Rough time to reach working competence in one skill, by priority. A P1 gap
# gets more time because it is the one that must be solid.
WEEKS_PER_SKILL = {"P1": 2, "P2": 2, "P3": 1}

MAX_MODULES = 6


@dataclass
class RoadmapModule:
    module: str
    category: Optional[str]
    priority: str
    skills: List[str] = field(default_factory=list)
    resources: List[Dict[str, str]] = field(default_factory=list)
    eta_weeks: int = 1
    start_week: int = 1
    jd_demand: int = 0

    @property
    def end_week(self) -> int:
        return self.start_week + self.eta_weeks - 1

    @property
    def week_label(self) -> str:
        if self.eta_weeks == 1:
            return f"Week {self.start_week}"
        return f"Week {self.start_week}-{self.end_week}"

    def as_dict(self) -> Dict[str, Any]:
        return {
            "week": self.week_label,
            "start_week": self.start_week,
            "end_week": self.end_week,
            "module": self.module,
            "category": self.category,
            "priority": self.priority,
            "skills": self.skills,
            "resources": self.resources,
            "eta_weeks": self.eta_weeks,
            "jd_demand": self.jd_demand,
            # The frontend tracks completion locally; this is the initial state.
            "completed": False,
        }


class LearningRoadmapService:
    async def generate(self, report: GapReport) -> Dict[str, Any]:
        """Build a roadmap from an aggregated gap report."""
        if not report.gaps:
            return {
                "modules": [],
                "weeks": [],
                "total_duration": "0 weeks",
                "total_modules": 0,
                "resources": [],
                "skills_covered": [],
                "jds_considered": report.jds_considered,
                "note": (
                    "No skill gaps were found across your target job descriptions. "
                    "Add more roles to see what to learn next."
                ),
            }

        modules = self._build_modules(report.gaps)
        modules = self._order_modules(modules)
        self._schedule(modules)

        total_weeks = max((module.end_week for module in modules), default=0)
        skills = [skill for module in modules for skill in module.skills]

        return {
            "modules": [module.as_dict() for module in modules],
            # Alias kept so the existing LearningRoadmapSchema shape still works.
            "weeks": [module.as_dict() for module in modules],
            "total_duration": f"{total_weeks} week{'s' if total_weeks != 1 else ''}",
            "total_modules": len(modules),
            "resources": resources_for(skills),
            "skills_covered": skills,
            "jds_considered": report.jds_considered,
            "note": None,
        }

    async def generate_roadmap(self, missing_skills: List[str]) -> Dict[str, Any]:
        """Build a roadmap from bare skill names, for callers without a report."""
        gaps = [
            AggregatedGap(skill=skill, normalized=skill.lower(), jd_count=1, priority="P2")
            for skill in missing_skills
            if str(skill).strip()
        ]
        from app.services.parsing.skill_vocabulary import category_of

        for gap in gaps:
            gap.category = category_of(gap.skill)
        return await self.generate(GapReport(gaps=gaps, jds_considered=1))

    # ---------------------------------------------------------------- internals

    def _build_modules(self, gaps: List[AggregatedGap]) -> List[RoadmapModule]:
        modules: List[RoadmapModule] = []

        for category, members in cluster_by_category(gaps).items():
            ordered = self._order_within_module(members)
            priority = min(
                (gap.priority for gap in ordered),
                key=lambda value: {"P1": 0, "P2": 1, "P3": 2}.get(value, 2),
            )
            modules.append(RoadmapModule(
                module=module_name(category),
                category=category,
                priority=priority,
                skills=[gap.skill for gap in ordered],
                resources=resources_for([gap.skill for gap in ordered]),
                eta_weeks=sum(WEEKS_PER_SKILL.get(gap.priority, 1) for gap in ordered),
                jd_demand=max(gap.jd_count for gap in ordered),
            ))

        return modules[:MAX_MODULES]

    def _order_within_module(self, gaps: List[AggregatedGap]) -> List[AggregatedGap]:
        """Prerequisites first, then by how many JDs demand the skill."""
        names = {gap.skill for gap in gaps}

        def sort_key(gap: AggregatedGap):
            prerequisite = prerequisite_of(gap.skill)
            # A skill whose prerequisite is also in this module comes second.
            depends_on_sibling = 1 if prerequisite in names else 0
            return (depends_on_sibling, -gap.jd_count, gap.skill)

        return sorted(gaps, key=sort_key)

    def _order_modules(self, modules: List[RoadmapModule]) -> List[RoadmapModule]:
        """Criticality first, then demand - but never before a prerequisite."""
        priority_rank = {"P1": 0, "P2": 1, "P3": 2}
        ordered = sorted(
            modules,
            key=lambda module: (priority_rank.get(module.priority, 2), -module.jd_demand, module.module),
        )
        return self._respect_prerequisites(ordered)

    def _respect_prerequisites(self, modules: List[RoadmapModule]) -> List[RoadmapModule]:
        """Move a module earlier if a later one teaches its prerequisite.

        Learning Kubernetes before Docker, or FastAPI before Python, wastes the
        first module - so the provider module is pulled in front.
        """
        result = list(modules)

        for _ in range(len(result)):
            swapped = False
            for index, module in enumerate(result):
                needed = {
                    prerequisite_of(skill)
                    for skill in module.skills
                    if prerequisite_of(skill)
                }
                if not needed:
                    continue

                for later in range(index + 1, len(result)):
                    if needed & set(result[later].skills):
                        result.insert(index, result.pop(later))
                        swapped = True
                        break
                if swapped:
                    break
            if not swapped:
                break

        return result

    def _schedule(self, modules: List[RoadmapModule]) -> None:
        week = 1
        for module in modules:
            module.start_week = week
            week += module.eta_weeks
