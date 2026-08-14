import pytest

from app.services.parsing.resume_parser import ResumeParserService
from app.services.parsing.jd_parser import JDParserService
from app.services.alignment.scorer import AlignmentScorerService


SAMPLE_RESUME_TEXT = """
John Doe
Senior Backend Engineer
john.doe@example.com | +1 415 555 0132

WORK EXPERIENCE
Acme Tech Bengaluru, Karnataka
Senior Backend Engineer January 2021 - Present
- Built event-driven APIs with Python and FastAPI
- Led migration to PostgreSQL and Docker
- Delivered Kubernetes-based deployment pipelines

SKILLS
Languages: Python, SQL
Frameworks: FastAPI
Infrastructure: PostgreSQL, Docker, Kubernetes
"""

SAMPLE_JD_TEXT = """
Backend Engineer
Company: Acme Tech

Requirements
- Python
- FastAPI
- PostgreSQL
- Kubernetes
- 5+ years experience
"""


def _get_nested(obj, *keys):
    value = obj
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        elif isinstance(value, (list, tuple)) and isinstance(key, int):
            value = value[key] if -len(value) <= key < len(value) else None
        else:
            value = getattr(value, key, None)
        if value is None:
            break
    return value


@pytest.mark.asyncio
async def test_resume_parser_extracts_core_resume_structure():
    service = ResumeParserService()
    parsed = await service.parse(SAMPLE_RESUME_TEXT)

    assert _get_nested(parsed, "personal_info", "name") == "John Doe"
    assert _get_nested(parsed, "personal_info", "email") == "john.doe@example.com"
    hard_skills = _get_nested(parsed, "skills", "hard_skills") or []
    assert "Python" in hard_skills
    assert "FastAPI" in hard_skills
    assert _get_nested(parsed, "experience", 0, "role") == "Senior Backend Engineer"
    assert _get_nested(parsed, "experience", 0, "company") == "Acme Tech"
    assert _get_nested(parsed, "total_experience_years") > 0


@pytest.mark.asyncio
async def test_jd_parser_extracts_requirements_and_experience_level():
    service = JDParserService()
    parsed = await service.parse(SAMPLE_JD_TEXT)

    assert _get_nested(parsed, "role") == "Backend Engineer"
    assert _get_nested(parsed, "company") == "Acme Tech"

    mandatory = _get_nested(parsed, "requirements", "mandatory_skills") or []
    assert "Python" in mandatory
    assert "Kubernetes" in mandatory
    assert _get_nested(parsed, "seniority") == "senior"
    assert _get_nested(parsed, "min_experience_years") == 5


@pytest.mark.asyncio
async def test_alignment_scorer_returns_structured_match_results():
    resume_service = ResumeParserService()
    jd_service = JDParserService()
    scorer = AlignmentScorerService()

    resume = await resume_service.parse(SAMPLE_RESUME_TEXT)
    jd = await jd_service.parse(SAMPLE_JD_TEXT)
    result = await scorer.score_resume_to_jd(resume, jd)

    # Scores are reported on a 0-100 percentage scale.
    assert 0.0 <= _get_nested(result, "alignment_score") <= 100.0
    assert 0.0 <= _get_nested(result, "skill_match_score") <= 100.0
    assert _get_nested(result, "feedback")
    assert isinstance(_get_nested(result, "missing_keywords"), list)
