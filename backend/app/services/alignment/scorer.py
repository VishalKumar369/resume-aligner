import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.jd import JobDescription
from app.models.resume import Resume
from app.schemas.analytics import (
    AlignmentResponseSchema,
    ExtractionHealthSchema,
    MissingSkillSchema,
    PartialSkillSchema,
)
from app.schemas.jd_structured import is_current_jd_schema
from app.schemas.structured import is_current_schema
from app.services.alignment import components
from app.services.alignment.llm_enhancer import LLMAlignmentEnhancer
from app.services.alignment.persistence import AlignmentPersistenceService
from app.services.alignment.skill_matcher import SkillMatcher, SkillMatchReport
from app.services.ats.ats_engine import ATSResult
from app.services.ats.ats_scorer import ATSScorerService
from app.services.parsing.jd_parser import JDParserService
from app.services.parsing.resume_parser import ResumeParserService

logger = logging.getLogger(__name__)

_PLACEHOLDER_ID = UUID(int=0)

# Weights follow docs/alignment-engine.md. Tool match is folded into skills
# because there is no separate data source for it. Any component without data
# is dropped and the rest are renormalised, so a resume with no projects is not
# scored as having irrelevant ones.
COMPONENT_WEIGHTS = {
    "skill_match": 0.40,
    "responsibility_match": 0.20,
    "project_match": 0.20,
    "seniority_match": 0.20,
}

# Below this extraction confidence the parsed resume is not trustworthy enough
# to present its score as a real match.
MIN_TRUSTED_CONFIDENCE = 0.3


class AlignmentScorerService:
    def __init__(
        self,
        skill_matcher: Optional[SkillMatcher] = None,
        ats_scorer: Optional[ATSScorerService] = None,
        enhancer: Optional[LLMAlignmentEnhancer] = None,
        use_llm: Optional[bool] = None,
    ):
        self.resume_parser = ResumeParserService()
        self.jd_parser = JDParserService()
        self.skill_matcher = skill_matcher or SkillMatcher()
        self.ats_scorer = ats_scorer or ATSScorerService()
        self.enhancer = enhancer or LLMAlignmentEnhancer()
        # None means "decide from configuration at call time".
        self._use_llm = use_llm

    async def calculate_alignment(
        self,
        resume_id: UUID,
        jd_id: UUID,
        db: Optional[AsyncSession] = None,
        resume_text: Optional[str] = None,
        jd_text: Optional[str] = None,
    ) -> AlignmentResponseSchema:
        resume = None
        jd = None

        if db is not None:
            resume = await db.get(Resume, resume_id)
            jd = await db.get(JobDescription, jd_id)
            if not resume or not jd:
                raise HTTPException(status_code=404, detail="Resume or JD not found")

        resume_text = resume_text or (resume.raw_text if resume else "")
        jd_text = jd_text or (jd.raw_text if jd else "")

        # A payload from an older schema is re-parsed rather than trusted: its
        # field shapes differ and would score wrongly, or not at all.
        resume_stored = resume.structured_data if resume else None
        jd_stored = jd.structured_data if jd else None

        resume_data = resume_stored if is_current_schema(resume_stored) else await self.resume_parser.parse(resume_text)
        jd_data = jd_stored if is_current_jd_schema(jd_stored) else await self.jd_parser.parse(jd_text)

        if db is not None:
            if resume is not None and resume_data is not resume_stored:
                resume.structured_data = resume_data
                db.add(resume)
            if jd is not None and jd_data is not jd_stored:
                jd.structured_data = jd_data
                db.add(jd)

        result = await self.score_resume_to_jd(
            resume_data,
            jd_data,
            resume_text=resume_text or "",
            extraction_meta=(resume.extraction_meta if resume else None),
        )
        result.resume_id = resume_id
        result.jd_id = jd_id
        result.extraction_health = self._extraction_health(resume, jd_text)

        if db is not None:
            persistence = AlignmentPersistenceService(db)
            saved = await persistence.save_alignment(
                resume_id=resume_id, jd_id=jd_id, result=result.model_dump()
            )
            # Let the caller fetch this run back from GET /alignment/{id}.
            result.alignment_id = saved.id

        return result

    async def score_resume_to_jd(
        self,
        resume_data: Dict[str, Any],
        jd_data: Dict[str, Any],
        resume_text: str = "",
        extraction_meta: Optional[Dict[str, Any]] = None,
    ) -> AlignmentResponseSchema:
        skills = self.skill_matcher.match(resume_data, jd_data)
        resume_years = self._resume_experience_years(resume_data)

        scored = self._components(skills, resume_data, jd_data, resume_years)
        enhancement = await self._enhance(resume_data, jd_data)
        if enhancement:
            # The model may only refine the one component keyword overlap
            # approximates badly; every other number stays deterministic.
            scored["responsibility_match"] = enhancement["responsibility_match"]

        weights = self._renormalized_weights(scored)
        alignment_score = round(
            sum(scored[name] * weights[name] for name in scored), 2
        )

        ats = self.ats_scorer.compute(
            resume_data=resume_data,
            jd_data=jd_data,
            resume_text=resume_text,
            extraction_meta=extraction_meta,
        )

        if not scored:
            return self._nothing_to_compare(skills, ats)

        return AlignmentResponseSchema(
            resume_id=_PLACEHOLDER_ID,
            jd_id=_PLACEHOLDER_ID,
            alignment_score=alignment_score,
            ats_score=ats.score,
            skill_match_score=skills.score,
            experience_match_score=scored.get("seniority_match", 0.0),
            missing_keywords=skills.missing_display_names,
            feedback=(enhancement or {}).get("feedback")
            or self._feedback(alignment_score, skills, scored),
            improvement_suggestions=self._suggestions(skills, scored, ats, enhancement),
            breakdown={name: round(value, 2) for name, value in scored.items()},
            component_weights=weights,
            matched_skills=skills.matched,
            partial_skills=[
                PartialSkillSchema(
                    skill=item.skill, covered_by=item.covered_by, category=item.category
                )
                for item in skills.partial
            ],
            missing_skills=[
                MissingSkillSchema(
                    skill=item.skill,
                    importance=item.importance,
                    priority=item.priority,
                    weight=round(item.weight, 2),
                )
                for item in skills.missing
            ],
            ats_breakdown=ats.breakdown,
            ats_warnings=ats.warnings,
        )

    # ---------------------------------------------------------------- internals

    def _components(
        self,
        skills: SkillMatchReport,
        resume_data: Dict[str, Any],
        jd_data: Dict[str, Any],
        resume_years: float,
    ) -> Dict[str, float]:
        candidates = {
            "skill_match": skills.score if skills.has_requirements else None,
            "responsibility_match": components.responsibility_overlap(resume_data, jd_data),
            "project_match": components.project_relevance(resume_data, jd_data),
            "seniority_match": components.seniority_match(resume_years, jd_data, resume_data),
        }
        return {name: value for name, value in candidates.items() if value is not None}

    def _renormalized_weights(self, scored: Dict[str, float]) -> Dict[str, float]:
        total = sum(COMPONENT_WEIGHTS[name] for name in scored)
        if total <= 0:
            return {name: 0.0 for name in scored}
        return {name: round(COMPONENT_WEIGHTS[name] / total, 4) for name in scored}

    def _nothing_to_compare(
        self, skills: SkillMatchReport, ats: ATSResult
    ) -> AlignmentResponseSchema:
        return AlignmentResponseSchema(
            resume_id=_PLACEHOLDER_ID,
            jd_id=_PLACEHOLDER_ID,
            alignment_score=0.0,
            ats_score=ats.score,
            skill_match_score=0.0,
            experience_match_score=0.0,
            missing_keywords=skills.missing_display_names,
            feedback=(
                "No requirements could be identified in the job description, so there "
                "is nothing to score this resume against."
            ),
            improvement_suggestions=[],
            ats_breakdown=ats.breakdown,
            ats_warnings=ats.warnings,
        )

    def _feedback(
        self, alignment_score: float, skills: SkillMatchReport, scored: Dict[str, float]
    ) -> str:
        critical = [item for item in skills.missing if item.priority == "P1"]

        if alignment_score >= 80:
            base = "Strong match for this role."
        elif alignment_score >= 60:
            base = "Reasonable match, with clear gaps to close."
        else:
            base = "Limited match against this role's requirements."

        if critical:
            names = ", ".join(item.skill for item in critical[:3])
            return f"{base} The most critical gaps are {names}."

        weakest = min(scored, key=scored.get) if scored else None
        if weakest and scored[weakest] < 60:
            readable = weakest.replace("_", " ")
            return f"{base} Your weakest area is {readable}."

        return base

    async def _enhance(
        self, resume_data: Dict[str, Any], jd_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Ask the LLM to refine the responsibility read, if one is configured.

        Any failure is swallowed: the deterministic score already stands on its
        own, so a provider outage must not fail an alignment request.
        """
        use_llm = self._use_llm
        if use_llm is None:
            use_llm = LLMAlignmentEnhancer.is_available()
        if not use_llm:
            return None

        try:
            return await self.enhancer.enhance(resume_data, jd_data)
        except Exception as exc:  # noqa: BLE001 - enhancement is optional
            logger.warning("LLM alignment enhancement failed, using deterministic score: %s", exc)
            return None

    def _suggestions(
        self,
        skills: SkillMatchReport,
        scored: Dict[str, float],
        ats: ATSResult,
        enhancement: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        if enhancement and enhancement.get("improvement_suggestions"):
            return enhancement["improvement_suggestions"][:6]

        suggestions: List[str] = []

        for item in skills.missing[:3]:
            label = "Critical" if item.priority == "P1" else (
                "Important" if item.priority == "P2" else "Bonus"
            )
            suggestions.append(f"{label}: add evidence of {item.skill} to your resume.")

        for item in skills.partial[:2]:
            suggestions.append(
                f"You have {item.covered_by} but the role asks for {item.skill} - "
                f"call out any direct {item.skill} exposure."
            )

        if scored.get("responsibility_match", 100.0) < 50:
            suggestions.append(
                "Rewrite your experience bullets to mirror the language used in the "
                "job's responsibilities."
            )

        suggestions.extend(ats.content_feedback[:2])
        return suggestions[:6]

    def _resume_experience_years(self, resume_data: Dict[str, Any]) -> float:
        """Read the computed total, tolerating payloads from the older schema."""
        value = resume_data.get("total_experience_years")
        if value is None:
            value = resume_data.get("experience_years", 0)
        try:
            return max(0.0, float(value or 0))
        except (TypeError, ValueError):
            return 0.0

    def _extraction_health(
        self, resume: Optional[Resume], jd_text: str
    ) -> ExtractionHealthSchema:
        """Report parse quality so a broken extraction is not read as a poor match."""
        warnings: List[str] = []
        resume_ok = True

        if resume is not None:
            meta = resume.extraction_meta or {}
            warnings.extend(meta.get("warnings", []))
            confidence = meta.get("confidence")
            if not (resume.raw_text or "").strip():
                resume_ok = False
                warnings.append("resume_text_empty")
            elif confidence is not None and confidence < MIN_TRUSTED_CONFIDENCE:
                resume_ok = False
                warnings.append("low_extraction_confidence")

        jd_ok = bool((jd_text or "").strip())
        if not jd_ok:
            warnings.append("jd_text_empty")

        return ExtractionHealthSchema(
            resume_ok=resume_ok,
            jd_ok=jd_ok,
            warnings=list(dict.fromkeys(warnings)),
        )
