import json
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.jd import JobDescription
from app.models.resume import Resume
from app.schemas.analytics import AlignmentResponseSchema
from app.services.ai.factory import AIFactory
from app.services.alignment.persistence import AlignmentPersistenceService
from app.services.parsing.jd_parser import JDParserService
from app.services.parsing.resume_parser import ResumeParserService


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

        if db is not None:
            persistence = AlignmentPersistenceService(db)
            await persistence.save_alignment(resume_id=resume_id, jd_id=jd_id, result=result.model_dump())

        return result

    async def score_resume_to_jd(self, resume_data: Dict[str, Any], jd_data: Dict[str, Any]) -> AlignmentResponseSchema:
        resume_skills = {skill.lower() for skill in resume_data.get("skills", {}).get("hard_skills", [])}
        jd_skills = {skill.lower() for skill in jd_data.get("requirements", {}).get("mandatory", [])}

        if not resume_skills and not jd_skills:
            alignment_score = 0.0
            skill_match_score = 0.0
            experience_match_score = 0.0
        else:
            matched_skills = sorted(resume_skills.intersection(jd_skills))
            missing_keywords = sorted(jd_skills.difference(resume_skills))

            skill_match_score = round((len(matched_skills) / len(jd_skills) * 100.0) if jd_skills else 100.0, 2)
            experience_years = max(int(resume_data.get("experience_years", 0) or 0), 0)
            required_experience = max(int(jd_data.get("experience_years", 0) or 0), 1)
            experience_match_score = round(min(100.0, (experience_years / required_experience) * 100.0), 2)
            alignment_score = round((skill_match_score * 0.7) + (experience_match_score * 0.3), 2)
            ats_score = round(min(100.0, alignment_score + 3.0), 2)

            feedback = "Resume aligns well with the role requirements." if alignment_score >= 80 else "Resume needs more targeted skill coverage."
            suggestions = [f"Add experience with {keyword}" for keyword in missing_keywords[:3]]

            return AlignmentResponseSchema(
                resume_id=UUID(int=0),
                jd_id=UUID(int=0),
                alignment_score=alignment_score,
                ats_score=ats_score,
                skill_match_score=skill_match_score,
                experience_match_score=experience_match_score,
                missing_keywords=missing_keywords,
                feedback=feedback,
                improvement_suggestions=suggestions,
            )

        return AlignmentResponseSchema(
            resume_id=UUID(int=0),
            jd_id=UUID(int=0),
            alignment_score=alignment_score,
            ats_score=0.0,
            skill_match_score=skill_match_score,
            experience_match_score=experience_match_score,
            missing_keywords=[],
            feedback="Resume needs more targeted skill coverage.",
            improvement_suggestions=[],
        )


        matched_skills = sorted(resume_skills.intersection(jd_skills))
        missing_keywords = sorted(jd_skills.difference(resume_skills))

        skill_match_score = round((len(matched_skills) / len(jd_skills) * 100.0) if jd_skills else 100.0, 2)
        experience_years = max(int(resume_data.get("experience_years", 0) or 0), 0)
        required_experience = max(int(jd_data.get("experience_years", 0) or 0), 1)
        experience_match_score = round(min(100.0, (experience_years / required_experience) * 100.0), 2)
        alignment_score = round((skill_match_score * 0.7) + (experience_match_score * 0.3), 2)
        ats_score = round(min(100.0, alignment_score + 3.0), 2)

        feedback = "Resume aligns well with the role requirements." if alignment_score >= 80 else "Resume needs more targeted skill coverage."
        suggestions = [f"Add experience with {keyword}" for keyword in missing_keywords[:3]]

        return AlignmentResponseSchema(
            resume_id=UUID(int=0),
            jd_id=UUID(int=0),
            alignment_score=alignment_score,
            ats_score=ats_score,
            skill_match_score=skill_match_score,
            experience_match_score=experience_match_score,
            missing_keywords=missing_keywords,
            feedback=feedback,
            improvement_suggestions=suggestions,
        )

