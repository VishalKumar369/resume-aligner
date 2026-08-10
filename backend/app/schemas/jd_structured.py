"""Validated contract for the JSON stored in `job_descriptions.structured_data`.

Mirrors `app/schemas/structured.py` on the resume side so alignment compares
two known shapes rather than two bags of keywords.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

JD_SCHEMA_VERSION = "1.0"


class JDRequirements(BaseModel):
    # Must-haves, drawn from the requirements/qualifications sections.
    mandatory_skills: List[str] = Field(default_factory=list)
    # Nice-to-haves, drawn from preferred/bonus sections. Kept separate so a
    # candidate is not penalised for missing an optional skill.
    preferred_skills: List[str] = Field(default_factory=list)
    # Canonical lowercase forms used for matching against a resume.
    normalized_mandatory: List[str] = Field(default_factory=list)
    normalized_preferred: List[str] = Field(default_factory=list)
    # Degree and certification requirements, verbatim.
    qualifications: List[str] = Field(default_factory=list)


class JDStructuredData(BaseModel):
    schema_version: str = JD_SCHEMA_VERSION
    role: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    work_mode: Optional[str] = None        # remote | hybrid | onsite
    employment_type: Optional[str] = None  # Full-time | Contract | Internship | ...
    seniority: Optional[str] = None        # intern | entry | mid | senior | staff | principal | lead
    min_experience_years: Optional[int] = None
    max_experience_years: Optional[int] = None
    requirements: JDRequirements = Field(default_factory=JDRequirements)
    responsibilities: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    extraction_meta: Dict[str, Any] = Field(default_factory=dict)


def is_current_jd_schema(payload: Optional[Dict[str, Any]]) -> bool:
    """Whether a stored `structured_data` blob matches the current JD contract."""
    return bool(payload) and payload.get("schema_version") == JD_SCHEMA_VERSION
