"""The non-skill components of the alignment score.

Responsibility overlap and project relevance use data that Phases 2 and 3
already extract but nothing consumed: JD responsibilities, resume experience
highlights, and project tech stacks.

Each returns `None` when the inputs it needs are absent, so the scorer can drop
the component and renormalise instead of scoring a missing input as zero.
"""

import re
from typing import Any, Dict, List, Optional, Set

from app.schemas.structured import entries
from app.services.parsing.skill_vocabulary import find_skills

# Words too common to signal anything about a match.
_STOPWORDS = frozenset("""
a an the and or but if then than that this these those with without within for
from into onto over under across about above below between during of to in on
at by as is are was were be been being have has had do does did will would can
could should may might must our your their its his her they them we you i it
you'll we'll role team work working works job position company using use used
new other more most such via per including include includes strong good great
excellent ability able experience experienced years year responsibilities
requirements qualifications end also across well etc
""".split())

_WORD = re.compile(r"[a-z][a-z0-9+#./-]{2,}")

# Full marks once this share of the JD's responsibility vocabulary is echoed by
# the resume. Demanding 100% would punish every real candidate.
RESPONSIBILITY_TARGET = 0.35

_SENIORITY_RANK = {
    "intern": 0, "entry": 1, "mid": 2, "senior": 3,
    "lead": 4, "staff": 4, "principal": 5,
}


def responsibility_overlap(
    resume_data: Dict[str, Any], jd_data: Dict[str, Any]
) -> Optional[float]:
    """How much of what the role asks for the resume actually describes doing."""
    jd_terms = _content_terms(jd_data.get("responsibilities") or [])
    if not jd_terms:
        return None

    resume_text = _resume_narrative(resume_data)
    if not resume_text.strip():
        return None

    resume_terms = _content_terms([resume_text])
    if not resume_terms:
        return None

    overlap = len(jd_terms & resume_terms) / len(jd_terms)
    return round(min(100.0, (overlap / RESPONSIBILITY_TARGET) * 100.0), 2)


def project_relevance(
    resume_data: Dict[str, Any], jd_data: Dict[str, Any]
) -> Optional[float]:
    """Share of the JD's skills demonstrated in the candidate's projects."""
    projects = entries(resume_data, "projects")
    if not projects:
        return None

    requirements = jd_data.get("requirements", {}) or {}
    wanted = {
        str(skill).lower()
        for skill in (requirements.get("normalized_mandatory") or [])
        if str(skill).strip()
    }
    if not wanted:
        return None

    demonstrated: Set[str] = set()
    for project in projects:
        for skill in project.get("tech_stack") or []:
            demonstrated.update(item.lower() for item in find_skills(str(skill)))
        for highlight in project.get("highlights") or []:
            demonstrated.update(item.lower() for item in find_skills(str(highlight)))
        if project.get("description"):
            demonstrated.update(item.lower() for item in find_skills(str(project["description"])))

    if not demonstrated:
        return 0.0

    return round((len(wanted & demonstrated) / len(wanted)) * 100.0, 2)


def seniority_match(
    resume_years: float, jd_data: Dict[str, Any], resume_data: Dict[str, Any]
) -> Optional[float]:
    """Years against the stated bar, falling back to seniority bands."""
    required = jd_data.get("min_experience_years")

    if required:
        ratio = resume_years / float(required)
        if ratio >= 1.0:
            return 100.0
        # Below the bar, but a near miss should not read as a total mismatch.
        return round(max(0.0, ratio * 100.0), 2)

    jd_level = _SENIORITY_RANK.get((jd_data.get("seniority") or "").lower())
    if jd_level is None:
        return None

    resume_level = _band_from_years(resume_years)
    distance = abs(jd_level - resume_level)
    return round(max(0.0, 100.0 - (distance * 25.0)), 2)


# ---------------------------------------------------------------------- helpers


def _band_from_years(years: float) -> int:
    if years < 1:
        return 1   # entry
    if years < 5:
        return 2   # mid
    if years < 9:
        return 3   # senior
    return 4       # lead / staff


def _content_terms(chunks: List[str]) -> Set[str]:
    terms: Set[str] = set()
    for chunk in chunks:
        for word in _WORD.findall(str(chunk).lower()):
            if word in _STOPWORDS:
                continue
            terms.add(_singularize(word))
    return terms


def _singularize(word: str) -> str:
    """Crude stemming so "services" and "service" count as the same term."""
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("es") and not word.endswith("ses"):
        return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _resume_narrative(resume_data: Dict[str, Any]) -> str:
    parts: List[str] = [str(resume_data.get("summary") or "")]
    for entry in entries(resume_data, "experience"):
        parts.append(str(entry.get("role") or ""))
        parts.extend(str(item) for item in entry.get("highlights") or [])
    for entry in entries(resume_data, "projects"):
        parts.extend(str(item) for item in entry.get("highlights") or [])
    return "\n".join(parts)
