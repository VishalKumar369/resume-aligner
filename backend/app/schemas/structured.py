"""Validated contract for the JSON stored in `resumes.structured_data`.

Every downstream feature - alignment, ATS scoring, skill gap, learning roadmap,
dashboard analytics - reads this shape, so it is versioned. Bump
`SCHEMA_VERSION` on any breaking change and treat older payloads as stale.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

SCHEMA_VERSION = "1.0"


class ContactLinks(BaseModel):
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    other: List[str] = Field(default_factory=list)


class PersonalInfo(BaseModel):
    name: Optional[str] = None
    title: Optional[str] = None  # headline under the name, e.g. "Senior Backend Engineer"
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    links: ContactLinks = Field(default_factory=ContactLinks)


class SkillSet(BaseModel):
    hard_skills: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)
    # Canonical lowercase forms used for matching against a JD.
    normalized: List[str] = Field(default_factory=list)
    # The resume's own grouping, e.g. {"Languages": ["Python", "SQL"]}.
    categories: Dict[str, List[str]] = Field(default_factory=dict)


class ExperienceEntry(BaseModel):
    company: Optional[str] = None
    role: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[str] = None  # "YYYY-MM"
    end_date: Optional[str] = None    # "YYYY-MM" or "present"
    duration_months: Optional[int] = None
    is_current: bool = False
    is_internship: bool = False
    highlights: List[str] = Field(default_factory=list)


class EducationEntry(BaseModel):
    degree: Optional[str] = None
    institution: Optional[str] = None
    location: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    score: Optional[str] = None  # "8.4 CGPA", "First Class", "3.9 GPA"
    highlights: List[str] = Field(default_factory=list)


class ProjectEntry(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tech_stack: List[str] = Field(default_factory=list)
    links: List[str] = Field(default_factory=list)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    highlights: List[str] = Field(default_factory=list)


class CertificationEntry(BaseModel):
    name: Optional[str] = None
    issuer: Optional[str] = None
    year: Optional[int] = None


class ResumeStructuredData(BaseModel):
    schema_version: str = SCHEMA_VERSION
    personal_info: PersonalInfo = Field(default_factory=PersonalInfo)
    summary: Optional[str] = None
    skills: SkillSet = Field(default_factory=SkillSet)
    experience: List[ExperienceEntry] = Field(default_factory=list)
    education: List[EducationEntry] = Field(default_factory=list)
    projects: List[ProjectEntry] = Field(default_factory=list)
    certifications: List[CertificationEntry] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)
    total_experience_years: float = 0.0
    # How this payload was produced: extractor name, confidence, warnings.
    extraction_meta: Dict[str, Any] = Field(default_factory=dict)


def is_current_schema(payload: Optional[Dict[str, Any]]) -> bool:
    """Whether a stored `structured_data` blob matches the current contract."""
    return bool(payload) and payload.get("schema_version") == SCHEMA_VERSION


def entries(payload: Optional[Dict[str, Any]], key: str) -> List[Dict[str, Any]]:
    """Read a list-of-objects field, tolerating payloads from an older schema.

    Pre-1.0 records stored `experience`, `education`, and `projects` as lists of
    plain strings. Consumers that expect objects would crash on those, so
    anything that is not a mapping is skipped.
    """
    values = (payload or {}).get(key) or []
    if not isinstance(values, list):
        return []
    return [item for item in values if isinstance(item, dict)]
