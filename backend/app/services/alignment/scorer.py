from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.jd import JobDescription
from app.models.resume import Resume
from app.schemas.analytics import AlignmentResponseSchema, ExtractionHealthSchema
from app.services.alignment.persistence import AlignmentPersistenceService
from app.services.parsing.jd_parser import JDParserService
from app.services.parsing.resume_parser import ResumeParserService

_PLACEHOLDER_ID = UUID(int=0)

# Below this extraction confidence the parsed resume is not trustworthy enough
# to present its score as a real match.
MIN_TRUSTED_CONFIDENCE = 0.3


class AlignmentScorerService:
    def __init__(self):
        self.resume_parser = ResumeParserService()
        self.jd_parser = JDParserService()

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

        resume_data = (resume.structured_data if resume and resume.structured_data else None) or await self.resume_parser.parse(resume_text)
        jd_data = (jd.structured_data if jd and jd.structured_data else None) or await self.jd_parser.parse(jd_text)

        if db is not None and resume is not None and jd is not None:
            if not resume.structured_data:
                resume.structured_data = resume_data
            if not jd.structured_data:
                jd.structured_data = jd_data
            db.add(resume)
            db.add(jd)

        result = await self.score_resume_to_jd(resume_data, jd_data)
        result.resume_id = resume_id
        result.jd_id = jd_id
        result.extraction_health = self._extraction_health(resume, jd_text)

        if db is not None:
            persistence = AlignmentPersistenceService(db)
            await persistence.save_alignment(resume_id=resume_id, jd_id=jd_id, result=result.model_dump())

        return result

    async def score_resume_to_jd(
        self, resume_data: Dict[str, Any], jd_data: Dict[str, Any]
    ) -> AlignmentResponseSchema:
        resume_skills = self._resume_skills(resume_data)
        jd_skills = self._jd_mandatory_skills(jd_data)

        if not resume_skills and not jd_skills:
            return AlignmentResponseSchema(
                resume_id=_PLACEHOLDER_ID,
                jd_id=_PLACEHOLDER_ID,
                alignment_score=0.0,
                ats_score=0.0,
                skill_match_score=0.0,
                experience_match_score=0.0,
                missing_keywords=[],
                feedback="No skills could be identified in either the resume or the job description.",
                improvement_suggestions=[],
            )

        matched_skills = sorted(resume_skills.intersection(jd_skills))
        missing_keywords = sorted(jd_skills.difference(resume_skills))

        skill_match_score = round((len(matched_skills) / len(jd_skills) * 100.0) if jd_skills else 100.0, 2)
        experience_years = max(self._resume_experience_years(resume_data), 0.0)
        required_experience = max(self._jd_required_years(jd_data), 1.0)
        experience_match_score = round(min(100.0, (experience_years / required_experience) * 100.0), 2)
        alignment_score = round((skill_match_score * 0.7) + (experience_match_score * 0.3), 2)
        ats_score = round(min(100.0, alignment_score + 3.0), 2)

        feedback = (
            "Resume aligns well with the role requirements."
            if alignment_score >= 80
            else "Resume needs more targeted skill coverage."
        )
        suggestions = [f"Add experience with {keyword}" for keyword in missing_keywords[:3]]

        return AlignmentResponseSchema(
            resume_id=_PLACEHOLDER_ID,
            jd_id=_PLACEHOLDER_ID,
            alignment_score=alignment_score,
            ats_score=ats_score,
            skill_match_score=skill_match_score,
            experience_match_score=experience_match_score,
            missing_keywords=missing_keywords,
            feedback=feedback,
            improvement_suggestions=suggestions,
        )

    def _resume_skills(self, resume_data: Dict[str, Any]) -> set:
        """Prefer canonical forms so "React.js" matches a JD asking for "React"."""
        skills = resume_data.get("skills", {}) or {}
        normalized = skills.get("normalized") or []
        source = normalized or skills.get("hard_skills") or []
        return {str(skill).lower() for skill in source if str(skill).strip()}

    def _jd_mandatory_skills(self, jd_data: Dict[str, Any]) -> set:
        """Score against must-haves only.

        Nice-to-haves live in `preferred_skills`; counting them as required
        penalised candidates for skills the posting never demanded.
        """
        requirements = jd_data.get("requirements", {}) or {}
        source = (
            requirements.get("normalized_mandatory")
            or requirements.get("mandatory_skills")
            or requirements.get("mandatory")   # pre-Phase-3 payloads
            or []
        )
        return {str(skill).lower() for skill in source if str(skill).strip()}

    def _jd_required_years(self, jd_data: Dict[str, Any]) -> float:
        value = jd_data.get("min_experience_years")
        if value is None:
            value = jd_data.get("experience_years", 0)
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    def _resume_experience_years(self, resume_data: Dict[str, Any]) -> float:
        """Read the computed total, tolerating payloads from the older schema."""
        value = resume_data.get("total_experience_years")
        if value is None:
            value = resume_data.get("experience_years", 0)
        try:
            return float(value or 0)
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
