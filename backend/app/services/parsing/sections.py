"""Split resume text into its canonical sections.

Resumes are written as labelled blocks ("WORK EXPERIENCE", "SKILLS", ...).
Recovering those boundaries is what lets the extractor read a company/role pair
or a "Languages: Python, SQL" line correctly, instead of scanning the whole
document for keywords.
"""

from enum import Enum
from typing import Dict, List, Optional

from app.services.parsing.section_utils import SectionBlocks, SectionMatcher


class Section(str, Enum):
    HEADER = "header"          # the contact block above the first real section
    SUMMARY = "summary"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    SKILLS = "skills"
    PROJECTS = "projects"
    CERTIFICATIONS = "certifications"
    ACHIEVEMENTS = "achievements"
    PUBLICATIONS = "publications"
    OTHER = "other"


_SECTION_ALIASES: Dict[Section, tuple] = {
    Section.SUMMARY: (
        "professional summary", "career summary", "career objective",
        "executive summary", "summary", "objective", "profile", "about me",
        "about", "professional profile",
    ),
    Section.EXPERIENCE: (
        "professional experience", "work experience", "employment history",
        "work history", "career history", "professional background",
        "relevant experience", "experience", "employment", "internships",
        "internship experience",
    ),
    Section.EDUCATION: (
        "educational qualifications", "academic qualifications", "education",
        "academics", "academic background", "qualifications",
    ),
    Section.SKILLS: (
        "technical skills", "core competencies", "skills & abilities",
        "areas of expertise", "technologies", "tech stack", "skill set",
        "skills", "competencies", "expertise",
    ),
    Section.PROJECTS: (
        "personal projects", "academic projects", "key projects",
        "selected projects", "projects", "portfolio",
    ),
    Section.CERTIFICATIONS: (
        "certifications & licenses", "certifications", "certificates",
        "licenses", "courses", "training",
    ),
    Section.ACHIEVEMENTS: (
        "achievements & awards", "honors & awards", "accomplishments",
        "achievements", "awards", "honors", "honours",
        "extracurricular activities", "extra-curricular", "activities",
        "leadership", "volunteering",
    ),
    Section.PUBLICATIONS: ("publications", "research", "papers"),
}

_MATCHER: SectionMatcher = SectionMatcher(_SECTION_ALIASES, Section.HEADER)


class ResumeSections(SectionBlocks):
    @property
    def found(self) -> List[Section]:
        """Sections that were actually labelled in the document."""
        return [section for section in self.order if section is not Section.HEADER]


def split_sections(text: str) -> ResumeSections:
    blocks, order = _MATCHER.split(text)
    return ResumeSections(blocks, order)


def match_section_header(line: str) -> Optional[Section]:
    return _MATCHER.match(line)
