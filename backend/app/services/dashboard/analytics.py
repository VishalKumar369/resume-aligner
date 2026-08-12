"""Dashboard aggregation over real persisted data.

Implements `docs/dashboard-analytics.md`. Every number traces back to rows the
user's own uploads produced - nothing is seeded or illustrative.

Aggregation runs per request. The data volume is small, and computing on read
means the dashboard can never show a stale score.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alignment import AlignmentScore
from app.models.jd import JobDescription
from app.models.resume import Resume
from app.models.version import ResumeVersion
from app.services.skill_gap.aggregator import GapReport, SkillGapAggregator

# Career readiness leans on how well the resume matches the roles targeted, with
# ATS readability as a secondary factor: a perfect match nobody can parse is not
# readiness.
READINESS_ALIGNMENT_WEIGHT = 0.65
READINESS_ATS_WEIGHT = 0.35

# Interview probability bands. Deliberately coarse: this is a heuristic over the
# user's own scores, not a prediction trained on hiring outcomes.
PROBABILITY_BANDS = (
    (80.0, "Strong"),
    (65.0, "High"),
    (45.0, "Moderate"),
    (0.0, "Low"),
)
PROBABILITY_BASIS = (
    "0.6 x JD alignment + 0.4 x ATS score, averaged over your most recent run "
    "per target role"
)
PROBABILITY_CAVEAT = (
    "Heuristic derived from your own scores. Not a prediction model trained on "
    "hiring outcomes."
)

TOP_GAPS = 8
RECENT_ACTIVITY = 8
TREND_POINTS = 12


@dataclass
class _LatestRun:
    jd_id: UUID
    alignment_score: float
    ats_score: float
    created_at: datetime
    analysis: Dict[str, Any]


class DashboardAnalyticsService:
    def __init__(self, aggregator: Optional[SkillGapAggregator] = None):
        self.aggregator = aggregator or SkillGapAggregator()

    async def get_summary(self, db: AsyncSession, user_id: Optional[UUID] = None) -> Dict[str, Any]:
        resumes = await self._resumes(db, user_id)
        jds = await self._jds(db, user_id)
        alignments = await self._alignments(db, user_id)
        versions = await self._versions(db, user_id)

        latest = self._latest_per_jd(alignments)
        report = self.aggregator.aggregate([run.analysis for run in latest])

        readiness = self._career_readiness(latest)
        alignment_scores = [run.alignment_score for run in latest]
        ats_scores = [run.ats_score for run in latest]

        return {
            "totals": {
                "resumes": len(resumes),
                "job_descriptions": len(jds),
                "alignments": len(alignments),
                "optimized_versions": len(versions),
                "target_roles": len(latest),
            },
            "total_resumes": len(resumes),
            "avg_alignment_score": self._mean(alignment_scores),
            "best_alignment_score": round(max(alignment_scores), 2) if alignment_scores else 0.0,
            "avg_ats_score": self._mean(ats_scores),
            "best_ats_score": round(max(ats_scores), 2) if ats_scores else 0.0,
            "career_readiness_index": readiness,
            "interview_probability": self._interview_probability(latest),
            "top_skill_gaps": [gap.skill for gap in report.gaps[:TOP_GAPS]],
            "skill_gap_detail": [gap.as_dict() for gap in report.gaps[:TOP_GAPS]],
            "partial_skills": report.partial[:TOP_GAPS],
            "readiness_trend": self._readiness_trend(alignments),
            "top_company_matches": await self._company_matches(db, latest),
            "recent_activity": self._recent_activity(resumes, jds, alignments, versions),
            "recommended_improvements": self._improvements(latest, report),
            "has_data": bool(latest),
        }

    async def get_gap_report(
        self, db: AsyncSession, user_id: Optional[UUID] = None
    ) -> GapReport:
        """Aggregated gaps, shared with the learning roadmap endpoint."""
        latest = self._latest_per_jd(await self._alignments(db, user_id))
        return self.aggregator.aggregate([run.analysis for run in latest])

    # ------------------------------------------------------------------ queries

    async def _resumes(self, db: AsyncSession, user_id: Optional[UUID]) -> List[Resume]:
        query = select(Resume).where(Resume.is_deleted == False)
        if user_id is not None:
            query = query.where(Resume.owner_id == user_id)
        return list((await db.execute(query.order_by(Resume.created_at.desc()))).scalars().all())

    async def _jds(self, db: AsyncSession, user_id: Optional[UUID]) -> List[JobDescription]:
        query = select(JobDescription).where(JobDescription.is_deleted == False)
        if user_id is not None:
            query = query.where(JobDescription.owner_id == user_id)
        return list((await db.execute(query.order_by(JobDescription.created_at.desc()))).scalars().all())

    async def _alignments(
        self, db: AsyncSession, user_id: Optional[UUID] = None
    ) -> List[AlignmentScore]:
        query = select(AlignmentScore).where(AlignmentScore.is_deleted == False)
        if user_id is not None:
            query = query.where(AlignmentScore.resume_id.in_(self._owned_resumes(user_id)))
        query = query.order_by(AlignmentScore.created_at.desc())
        return list((await db.execute(query)).scalars().all())

    async def _versions(
        self, db: AsyncSession, user_id: Optional[UUID] = None
    ) -> List[ResumeVersion]:
        query = select(ResumeVersion).where(ResumeVersion.is_deleted == False)
        if user_id is not None:
            query = query.where(ResumeVersion.resume_id.in_(self._owned_resumes(user_id)))
        query = query.order_by(ResumeVersion.created_at.desc())
        return list((await db.execute(query)).scalars().all())

    def _owned_resumes(self, user_id: UUID):
        """Alignments and versions inherit ownership from their resume."""
        return select(Resume.id).where(
            Resume.owner_id == user_id, Resume.is_deleted == False
        )

    # ---------------------------------------------------------------- internals

    def _latest_per_jd(self, alignments: List[AlignmentScore]) -> List[_LatestRun]:
        """One run per target role - the newest.

        Averaging every historical run would let a single JD scored ten times
        dominate the dashboard.
        """
        seen: Dict[UUID, _LatestRun] = {}
        for row in alignments:  # already newest-first
            if row.jd_id in seen:
                continue
            seen[row.jd_id] = _LatestRun(
                jd_id=row.jd_id,
                alignment_score=float(row.total_alignment_score or 0.0),
                ats_score=float(row.ats_score or 0.0),
                created_at=row.created_at,
                analysis=row.analysis_data or {},
            )
        return list(seen.values())

    def _career_readiness(self, latest: List[_LatestRun]) -> float:
        if not latest:
            return 0.0
        alignment = self._mean([run.alignment_score for run in latest])
        ats = self._mean([run.ats_score for run in latest])
        return round(
            alignment * READINESS_ALIGNMENT_WEIGHT + ats * READINESS_ATS_WEIGHT, 2
        )

    def _interview_probability(self, latest: List[_LatestRun]) -> Dict[str, Any]:
        if not latest:
            return {
                "band": "Unknown",
                "score": 0.0,
                "basis": PROBABILITY_BASIS,
                "caveat": PROBABILITY_CAVEAT,
            }

        score = self._mean([
            run.alignment_score * 0.6 + run.ats_score * 0.4 for run in latest
        ])
        band = next(label for threshold, label in PROBABILITY_BANDS if score >= threshold)
        return {
            "band": band,
            "score": score,
            "basis": PROBABILITY_BASIS,
            "caveat": PROBABILITY_CAVEAT,
        }

    def _readiness_trend(self, alignments: List[AlignmentScore]) -> List[Dict[str, Any]]:
        """Alignment over time, oldest first, so a chart reads left to right."""
        points = [
            {
                "date": row.created_at.date().isoformat() if row.created_at else None,
                "alignment_score": round(float(row.total_alignment_score or 0.0), 2),
                "ats_score": round(float(row.ats_score or 0.0), 2),
            }
            for row in reversed(alignments[:TREND_POINTS])
        ]
        return points

    async def _company_matches(
        self, db: AsyncSession, latest: List[_LatestRun]
    ) -> List[Dict[str, Any]]:
        if not latest:
            return []

        jd_ids = [run.jd_id for run in latest]
        rows = (await db.execute(
            select(JobDescription).where(JobDescription.id.in_(jd_ids))
        )).scalars().all()
        by_id = {row.id: row for row in rows}

        # One row per company, not per posting: a company with four saved roles
        # should appear once, represented by its best match.
        best: Dict[str, Dict[str, Any]] = {}

        for run in latest:
            jd = by_id.get(run.jd_id)
            if jd is None:
                continue

            company = (jd.company_name or "Unknown company").strip()
            key = company.lower()
            existing = best.get(key)

            if existing is None:
                best[key] = {
                    "company": company,
                    "role": jd.title,
                    "jd_id": str(jd.id),
                    "alignment_score": round(run.alignment_score, 2),
                    "ats_score": round(run.ats_score, 2),
                    "analyzed_at": run.created_at.isoformat() if run.created_at else None,
                    "roles_tracked": 1,
                }
                continue

            existing["roles_tracked"] += 1
            if run.alignment_score > existing["alignment_score"]:
                existing.update({
                    "role": jd.title,
                    "jd_id": str(jd.id),
                    "alignment_score": round(run.alignment_score, 2),
                    "ats_score": round(run.ats_score, 2),
                    "analyzed_at": run.created_at.isoformat() if run.created_at else None,
                })

        return sorted(best.values(), key=lambda item: -item["alignment_score"])

    def _recent_activity(
        self,
        resumes: List[Resume],
        jds: List[JobDescription],
        alignments: List[AlignmentScore],
        versions: List[ResumeVersion],
    ) -> List[Dict[str, Any]]:
        events: List[Tuple[datetime, Dict[str, Any]]] = []

        for resume in resumes[:RECENT_ACTIVITY]:
            events.append((resume.created_at, {
                "action": "Resume uploaded",
                "target": resume.label or resume.filename,
            }))
        for jd in jds[:RECENT_ACTIVITY]:
            events.append((jd.created_at, {
                "action": "Job description added",
                "target": " - ".join(part for part in (jd.company_name, jd.title) if part) or "Untitled",
            }))
        for row in alignments[:RECENT_ACTIVITY]:
            events.append((row.created_at, {
                "action": "Alignment generated",
                "target": f"{round(float(row.total_alignment_score or 0.0), 1)}% match",
            }))
        for version in versions[:RECENT_ACTIVITY]:
            events.append((version.created_at, {
                "action": "Resume optimized",
                "target": version.label or version.filename,
            }))

        events = [event for event in events if event[0] is not None]
        events.sort(key=lambda item: item[0], reverse=True)

        return [
            {**payload, "date": moment.date().isoformat(), "at": moment.isoformat()}
            for moment, payload in events[:RECENT_ACTIVITY]
        ]

    def _improvements(self, latest: List[_LatestRun], report: GapReport) -> List[Dict[str, str]]:
        """Concrete next actions, drawn from the stored analyses."""
        improvements: List[Dict[str, str]] = []

        for gap in report.gaps[:3]:
            roles = "target role" if gap.jd_count == 1 else f"{gap.jd_count} target roles"
            improvements.append({
                "text": f"Add evidence of {gap.skill} - required by your {roles}.",
                "priority": "high" if gap.priority == "P1" else "medium",
            })

        seen = {item["text"] for item in improvements}
        for run in latest:
            for warning in (run.analysis.get("ats_warnings") or [])[:2]:
                if warning not in seen:
                    seen.add(warning)
                    improvements.append({"text": warning, "priority": "medium"})

        for entry in report.partial[:2]:
            improvements.append({
                "text": (
                    f"You have {entry.get('covered_by')} but roles ask for "
                    f"{entry.get('skill')} - call out any direct exposure."
                ),
                "priority": "low",
            })

        return improvements[:6]

    def _mean(self, values: List[float]) -> float:
        return round(sum(values) / len(values), 2) if values else 0.0
