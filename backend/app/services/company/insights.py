"""Company insights derived strictly from the user's own job descriptions.

The previous implementation returned a hardcoded tech stack, culture list, and
interview tips for any company id - inventing claims about named real
organisations. Every field here traces to a posting the user actually saved, so
the endpoint reports what those postings say and nothing more.
"""

import re
from collections import Counter, defaultdict
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
        self, db: AsyncSession, company_id: str, owner_id: Optional[UUID] = None
    ) -> Optional[Dict[str, Any]]:
        """Insights for a company, or None if the user has saved no JDs for it.

        `company_id` may be the stored company name or its slug.
        """
        jds = await self._matching_jds(db, company_id, owner_id)
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

        alignments = await self._alignments(db, [jd.id for jd in jds])
        scores = [float(row.total_alignment_score or 0.0) for row in alignments]

        # Newest run per JD, so each posting can show your latest match and link
        # to that analysis (with its tailored resume).
        latest_by_jd: Dict[UUID, Any] = {}
        for row in alignments:  # already newest-first
            latest_by_jd.setdefault(row.jd_id, row)

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
            "postings": [self._posting_detail(jd, latest_by_jd.get(jd.id)) for jd in jds],
            "source": "Derived from the job descriptions you saved for this company.",
        }

    def _posting_detail(self, jd: Any, latest: Any) -> Dict[str, Any]:
        """One posting's own details: role, requirements, and your latest match.

        `latest` is the newest alignment run for this JD (or None), carrying the
        resume and run ids so the client can open the full analysis view.
        """
        data = (getattr(jd, "structured_data", None) or {})
        requirements = data.get("requirements", {}) or {}
        return {
            "jd_id": str(jd.id),
            "title": jd.title,
            "url": jd.url,
            "added_at": jd.created_at.isoformat() if getattr(jd, "created_at", None) else None,
            "seniority": data.get("seniority"),
            "location": data.get("location"),
            "work_mode": data.get("work_mode"),
            "employment_type": data.get("employment_type"),
            "mandatory_skills": [str(s) for s in (requirements.get("mandatory_skills") or [])][:TOP_SKILLS],
            "preferred_skills": [str(s) for s in (requirements.get("preferred_skills") or [])][:TOP_SKILLS],
            "your_alignment": round(float(latest.total_alignment_score or 0.0), 2) if latest else None,
            "your_ats": round(float(latest.ats_score or 0.0), 2) if latest else None,
            "resume_id": str(latest.resume_id) if latest else None,
            "alignment_id": str(latest.id) if latest else None,
        }

    async def list_companies(
        self, db: AsyncSession, owner_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """One summary card per company the user has saved a posting for."""
        jds = await self._owner_jds(db, owner_id)
        jd_ids = [jd.id for jd in jds]
        alignments = await self._alignments(db, jd_ids)
        return self.summarize_companies(jds, alignments)

    def summarize_companies(
        self, jds: List[Any], alignments: List[Any]
    ) -> List[Dict[str, Any]]:
        """Cards for the Company Intelligence index. Pure, so it is unit-testable.

        Postings with a company name are grouped into one card per company.
        Postings without one (the parser found no company) still appear, each as
        its own role card, so nothing the user analyzed is hidden.

        `alignments` must be newest-first, so the first run seen for a JD is its
        latest - what the gap count is built from.
        """
        aligns_by_jd: Dict[Any, List[Any]] = defaultdict(list)
        for row in alignments:
            aligns_by_jd[row.jd_id].append(row)

        named: Dict[str, List[Any]] = {}
        unnamed: List[Any] = []
        for jd in jds:
            name = str(getattr(jd, "company_name", None) or "").strip()
            if name:
                named.setdefault(slugify(name), []).append(jd)
            else:
                unnamed.append(jd)

        cards = [self._company_card(slug, group, aligns_by_jd) for slug, group in named.items()]
        cards += [self._role_card(jd, aligns_by_jd.get(jd.id, [])) for jd in unnamed]

        # Best matches first; ties broken by breadth of postings, then name.
        return sorted(
            cards,
            key=lambda card: (
                -(card["your_best_alignment"] or 0.0),
                -card["jd_count"],
                card["company"].lower(),
            ),
        )

    def _company_card(
        self, slug: str, group: List[Any], aligns_by_jd: Dict[Any, List[Any]]
    ) -> Dict[str, Any]:
        scores: List[float] = []
        latest_analyses: List[Dict[str, Any]] = []
        demanded = Counter()

        for jd in group:
            runs = aligns_by_jd.get(jd.id, [])
            scores.extend(float(run.total_alignment_score or 0.0) for run in runs)
            if runs:
                latest_analyses.append(runs[0].analysis_data or {})
            requirements = (getattr(jd, "structured_data", None) or {}).get("requirements", {}) or {}
            demanded.update(str(skill) for skill in requirements.get("mandatory_skills") or [])

        report = self.aggregator.aggregate(latest_analyses)
        dates = [jd.created_at for jd in group if getattr(jd, "created_at", None)]

        return {
            "company_id": slug,
            "company": str(group[0].company_name).strip(),
            "named": True,
            "jd_count": len(group),
            "roles": self._unique([jd.title for jd in group]),
            "demanded_skills": [skill for skill, _ in demanded.most_common(6)],
            "your_best_alignment": round(max(scores), 2) if scores else None,
            "your_average_alignment": round(sum(scores) / len(scores), 2) if scores else None,
            "gap_count": len(report.gaps),
            "last_activity": max(dates).isoformat() if dates else None,
        }

    def _role_card(self, jd: Any, runs: List[Any]) -> Dict[str, Any]:
        """A single un-companied posting, so it still shows and links to its
        analysis (company_id is the JD id, routing to the scoped view)."""
        latest = runs[0] if runs else None
        scores = [float(run.total_alignment_score or 0.0) for run in runs]
        requirements = (getattr(jd, "structured_data", None) or {}).get("requirements", {}) or {}
        missing = (latest.analysis_data or {}).get("missing_skills", []) if latest else []
        return {
            "company_id": str(jd.id),
            "company": jd.title or "Untitled role",
            "named": False,
            "jd_id": str(jd.id),
            "resume_id": str(latest.resume_id) if latest else None,
            "alignment_id": str(latest.id) if latest else None,
            "jd_count": 1,
            "roles": [jd.title] if jd.title else [],
            "demanded_skills": [str(skill) for skill in (requirements.get("mandatory_skills") or [])][:6],
            "your_best_alignment": round(max(scores), 2) if scores else None,
            "your_average_alignment": round(sum(scores) / len(scores), 2) if scores else None,
            "gap_count": len(missing),
            "last_activity": jd.created_at.isoformat() if getattr(jd, "created_at", None) else None,
        }

    # ---------------------------------------------------------------- internals

    async def _owner_jds(
        self, db: AsyncSession, owner_id: Optional[UUID] = None
    ) -> List[JobDescription]:
        query = select(JobDescription).where(JobDescription.is_deleted == False)
        if owner_id is not None:
            query = query.where(JobDescription.owner_id == owner_id)
        return list((await db.execute(
            query.order_by(JobDescription.created_at.desc())
        )).scalars().all())

    async def _matching_jds(
        self, db: AsyncSession, company_id: str, owner_id: Optional[UUID] = None
    ) -> List[JobDescription]:
        query = select(JobDescription).where(JobDescription.is_deleted == False)
        if owner_id is not None:
            query = query.where(JobDescription.owner_id == owner_id)
        rows = (await db.execute(
            query.order_by(JobDescription.created_at.desc())
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
