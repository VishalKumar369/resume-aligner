"""Aggregate skill gaps across every job description a user is targeting.

A gap that appears in one posting is a detail; a gap that appears in all of them
is the thing worth learning next. `docs/skill-gap-engine.md` calls this the
commonality gap, and it is what drives both the dashboard's top gaps and the
learning roadmap's ordering.

Gaps are read from stored alignment runs, so this reuses the weighting and
P1/P2/P3 ranking the Phase 4 scorer already produced rather than re-deriving it.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.services.parsing.skill_vocabulary import category_of, normalize_skill

# How much each priority contributes to a gap's overall weight.
PRIORITY_WEIGHT = {"P1": 3.0, "P2": 2.0, "P3": 0.5}


@dataclass
class AggregatedGap:
    skill: str
    normalized: str
    category: Optional[str] = None
    # How many of the user's target JDs ask for this and do not find it.
    jd_count: int = 0
    # Strongest priority seen across those JDs.
    priority: str = "P3"
    # Whether some JD counted it as a must-have.
    mandatory: bool = False
    score: float = 0.0

    def as_dict(self) -> Dict[str, Any]:
        return {
            "skill": self.skill,
            "category": self.category,
            "priority": self.priority,
            "jd_count": self.jd_count,
            "mandatory": self.mandatory,
            "score": round(self.score, 2),
        }


@dataclass
class GapReport:
    gaps: List[AggregatedGap] = field(default_factory=list)
    partial: List[Dict[str, Any]] = field(default_factory=list)
    jds_considered: int = 0

    @property
    def top_skills(self) -> List[str]:
        return [gap.skill for gap in self.gaps]

    def critical(self) -> List[AggregatedGap]:
        return [gap for gap in self.gaps if gap.priority == "P1"]


class SkillGapAggregator:
    """Combines the gap lists of many alignment runs into one ranked view."""

    def aggregate(self, analyses: List[Dict[str, Any]]) -> GapReport:
        """`analyses` is one `analysis_data` blob per JD (use the latest run)."""
        buckets: Dict[str, AggregatedGap] = {}
        partial: Dict[str, Dict[str, Any]] = {}

        for analysis in analyses:
            for raw in (analysis or {}).get("missing_skills") or []:
                self._absorb(buckets, raw)
            for raw in (analysis or {}).get("partial_skills") or []:
                self._absorb_partial(partial, raw)

        for gap in buckets.values():
            # Frequency across postings is the dominant signal; priority breaks
            # ties between equally common gaps.
            gap.score = gap.jd_count * PRIORITY_WEIGHT.get(gap.priority, 0.5)

        ranked = sorted(
            buckets.values(),
            key=lambda gap: (-gap.score, -gap.jd_count, gap.skill),
        )
        return GapReport(
            gaps=ranked,
            partial=list(partial.values()),
            jds_considered=len(analyses),
        )

    # ---------------------------------------------------------------- internals

    def _absorb(self, buckets: Dict[str, AggregatedGap], raw: Any) -> None:
        skill, priority, importance = self._read_gap(raw)
        if not skill:
            return

        key = normalize_skill(skill).lower()
        gap = buckets.get(key)
        if gap is None:
            gap = AggregatedGap(
                skill=normalize_skill(skill),
                normalized=key,
                category=category_of(skill),
            )
            buckets[key] = gap

        gap.jd_count += 1
        gap.mandatory = gap.mandatory or importance == "mandatory"
        if self._is_stronger(priority, gap.priority):
            gap.priority = priority

    def _absorb_partial(self, partial: Dict[str, Dict[str, Any]], raw: Any) -> None:
        if not isinstance(raw, dict):
            return
        skill = str(raw.get("skill") or "").strip()
        if not skill:
            return

        key = normalize_skill(skill).lower()
        entry = partial.setdefault(key, {
            "skill": normalize_skill(skill),
            "covered_by": raw.get("covered_by"),
            "category": raw.get("category") or category_of(skill),
            "jd_count": 0,
        })
        entry["jd_count"] += 1

    def _read_gap(self, raw: Any):
        """Read a gap entry, tolerating the plain-string form of older rows."""
        if isinstance(raw, dict):
            return (
                str(raw.get("skill") or "").strip(),
                str(raw.get("priority") or "P3"),
                str(raw.get("importance") or "mandatory"),
            )
        return str(raw or "").strip(), "P2", "mandatory"

    def _is_stronger(self, candidate: str, current: str) -> bool:
        order = {"P1": 0, "P2": 1, "P3": 2}
        return order.get(candidate, 2) < order.get(current, 2)


def cluster_by_category(gaps: List[AggregatedGap]) -> Dict[str, List[AggregatedGap]]:
    """Group gaps into learnable modules.

    Docker and Kubernetes are one subject, not two; learning them together is
    more efficient than treating each as a separate module.
    """
    clusters: Dict[str, List[AggregatedGap]] = defaultdict(list)
    for gap in gaps:
        clusters[gap.category or "other"].append(gap)
    return dict(clusters)
