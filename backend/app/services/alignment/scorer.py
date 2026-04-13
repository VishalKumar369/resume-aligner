import json
from typing import Dict, Any, List
from uuid import UUID
from app.schemas.analytics import AlignmentResponseSchema
from app.services.ai.factory import AIFactory

class AlignmentScorerService:
    async def calculate_alignment(self, resume_id: UUID, jd_id: UUID, resume_text: str, jd_text: str) -> AlignmentResponseSchema:
        """
        Computes semantic alignment between resume and JD using the configured AI provider.
        """
        provider = AIFactory.get_provider()
        
        prompt = f"""
        Analyze the semantic alignment between this resume and the job description.
        Provide scores for total alignment, skill match, and experience depth.
        Identify missing keywords and provide high-level feedback and improvement suggestions.
        
        RETURN ONLY A JSON OBJECT with this structure:
        {{
            "alignment_score": float,
            "ats_score": float,
            "skill_match_score": float,
            "experience_match_score": float,
            "missing_keywords": [str],
            "feedback": str,
            "improvement_suggestions": [str]
        }}
        
        RESUME:
        {resume_text[:4000]}
        
        JOB DESCRIPTION:
        {jd_text[:4000]}
        """
        
        messages = [{"role": "user", "content": prompt}]
        response_text = await provider.chat_completion(messages, temperature=0.3)
        
        try:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            data = json.loads(response_text[start:end])
            return AlignmentResponseSchema(
                resume_id=resume_id,
                jd_id=jd_id,
                **data
            )
        except Exception:
            return AlignmentResponseSchema(
                resume_id=resume_id,
                jd_id=jd_id,
                alignment_score=0.0,
                ats_score=0.0,
                skill_match_score=0.0,
                experience_match_score=0.0,
                missing_keywords=[],
                feedback="Error analyzing alignment",
                improvement_suggestions=[]
            )
