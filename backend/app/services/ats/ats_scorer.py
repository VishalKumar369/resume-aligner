import json
from typing import List, Dict
from app.schemas.analytics import ATSScoreSchema
from app.services.ai.factory import AIFactory

class ATSScorerService:
    @staticmethod
    async def compute_score(resume_text: str, jd_text: str) -> ATSScoreSchema:
        """
        Calculates a weighted ATS score based on:
        - Keyword density (40%)
        - Metrics presence (20%)
        - Section completeness (10%)
        - Bullet point clarity (10%)
        - Formatting best practices (20%)
        """
        provider = AIFactory.get_provider()
        
        prompt = f"""
        Analyze the following resume against the job description.
        Provide a weighted ATS score (0-100) and a breakdown across these categories: Keywords, Metrics, Structure, Clarity, Formatting.
        Also provide specific formatting and content feedback.
        
        RETURN ONLY A JSON OBJECT with this structure:
        {{
            "score": float,
            "breakdown": {{"Keywords": float, "Metrics": float, "Structure": float, "Clarity": float, "Formatting": float}},
            "formatting_feedback": [str],
            "content_feedback": [str]
        }}
        
        RESUME:
        {resume_text[:4000]}
        
        JOB DESCRIPTION:
        {jd_text[:4000]}
        """
        
        messages = [{"role": "user", "content": prompt}]
        response_text = await provider.chat_completion(messages, temperature=0.2)
        
        # Parse JSON from response
        try:
            # Simple cleaning to find JSON block
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            data = json.loads(response_text[start:end])
            return ATSScoreSchema(**data)
        except Exception as e:
            # Fallback for parsing errors
            return ATSScoreSchema(
                score=0.0,
                breakdown={"Keywords": 0, "Metrics": 0, "Structure": 0, "Clarity": 0, "Formatting": 0},
                formatting_feedback=["Error parsing AI response"],
                content_feedback=[str(e)]
            )
