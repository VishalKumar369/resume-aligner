"""Company insights derived strictly from the user's own job descriptions.

The previous implementation returned a hardcoded tech stack, culture list, and
interview tips for any company id - inventing claims about named real
organisations. Every field here traces to a posting the user actually saved, so
the endpoint reports what those postings say and nothing more.
"""

import re
from collections import Counter
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alignment import AlignmentScore
from app.models.jd import JobDescription
from app.services.skill_gap.aggregator import SkillGapAggregator

TOP_SKILLS = 12


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")


class CompanyInsightsService:
    def __init__(self, aggregator: Optional[SkillGapAggregator] = None):
        self.aggregator = aggregator or SkillGapAggregator()

    async def get_insights(
        self, db: AsyncSession, company_id: str
    ) -> Optional[Dict[str, Any]]:
        """Insights for a company, or None if the user has saved no JDs for it.

        `company_id` may be the stored company name or its slug.
        """
        jds = await self._matching_jds(db, company_id)
        if not jds:
            return None

        analyses = await self._latest_analyses(db, [jd.id for jd in jds])
        report = self.aggregator.aggregate(analyses)

        mandatory = Counter()
        preferred = Counter()
        for jd in jds:
            requirements = (jd.structured_data or {}).get("requirements", {}) or {}
            mandatory.update(str(s) for s in requirements.get("mandatory_skills") or [])
            preferred.update(str(s) for s in requirements.get("preferred_skills") or [])

        scores = [
            float(score.total_alignment_score or 0.0)
            for score in await self._alignments(db, [jd.id for jd in jds])
        ]

        return {
            "company_id": slugify(jds[0].company_name or company_id),
            "company": jds[0].company_name or company_id,
            "jd_count": len(jds),
            "roles": self._unique([jd.title for jd in jds]),
            "seniority_levels": self._field_values(jds, "seniority"),
            "locations": self._field_values(jds, "location"),
            "work_modes": self._field_values(jds, "work_mode"),
            "employment_types": self._field_values(jds, "employment_type"),
            "demanded_skills": [skill for skill, _ in mandatory.most_common(TOP_SKILLS)],
            "preferred_skills": [skill for skill, _ in preferred.most_common(TOP_SKILLS)],
            "your_best_alignment": round(max(scores), 2) if scores else None,
            "your_average_alignment": round(sum(scores) / len(scores), 2) if scores else None,
            "your_gaps_here": [gap.as_dict() for gap in report.gaps[:TOP_SKILLS]],
            "postings": [
                {
                    "jd_id": str(jd.id),
                    "title": jd.title,
                    "url": jd.url,
                    "added_at": jd.created_at.isoformat() if jd.created_at else None,
                }
                for jd in jds
            ],
            "source": "Derived from the job descriptions you saved for this company.",
        }

    # ---------------------------------------------------------------- internals

    async def _matching_jds(self, db: AsyncSession, company_id: str) -> List[JobDescription]:
        rows = (await db.execute(
            select(JobDescription)
            .where(JobDescription.is_deleted == False)
            .order_by(JobDescription.created_at.desc())
        )).scalars().all()

        target = slugify(company_id)
        return [
            jd for jd in rows
            if jd.company_name and (
                slugify(jd.company_name) == target or target in slugify(jd.company_name)
            )
        ]

    async def _alignments(self, db: AsyncSession, jd_ids: List[UUID]) -> List[AlignmentScore]:
        if not jd_ids:
            return []
        return list((await db.execute(
            select(AlignmentScore)
            .where(AlignmentScore.jd_id.in_(jd_ids), AlignmentScore.is_deleted == False)
            .order_by(AlignmentScore.created_at.desc())
        )).scalars().all())

    async def _latest_analyses(self, db: AsyncSession, jd_ids: List[UUID]) -> List[Dict[str, Any]]:
        """The newest analysis per JD, so one re-scored role cannot dominate."""
        seen: Dict[UUID, Dict[str, Any]] = {}
        for row in await self._alignments(db, jd_ids):
            if row.jd_id not in seen:
                seen[row.jd_id] = row.analysis_data or {}
        return list(seen.values())

    def _unique(self, values: List[Optional[str]]) -> List[str]:
        seen: List[str] = []
        for value in values:
            text = str(value or "").strip()
            if text and text not in seen:
                seen.append(text)
        return seen

    def _field_values(self, jds: List[JobDescription], key: str) -> List[str]:
        return self._unique([(jd.structured_data or {}).get(key) for jd in jds])
