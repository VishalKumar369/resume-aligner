"""Split resume text into its canonical sections.

Resumes are written as labelled blocks ("WORK EXPERIENCE", "SKILLS", ...).
Recovering those boundaries is what lets the extractor read a company/role pair
or a "Languages: Python, SQL" line correctly, instead of scanning the whole
document for keywords.
"""

import re
from enum import Enum
from typing import Dict, List, Optional


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


# Longest aliases are matched first so "work experience" wins over "experience".
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

_ALIAS_LOOKUP = {
    alias: section
    for section, aliases in _SECTION_ALIASES.items()
    for alias in aliases
}
_SORTED_ALIASES = sorted(_ALIAS_LOOKUP, key=len, reverse=True)

_NON_LETTERS = re.compile(r"[^a-z& ]+")
_MAX_HEADER_WORDS = 5


class ResumeSections:
    """Line groups keyed by section, preserving document order."""

    def __init__(self, blocks: Dict[Section, List[str]], order: List[Section]):
        self._blocks = blocks
        self.order = order

    def get(self, section: Section) -> List[str]:
        return self._blocks.get(section, [])

    def text(self, section: Section) -> str:
        return "\n".join(self.get(section)).strip()

    def has(self, section: Section) -> bool:
        return bool(self._blocks.get(section))

    @property
    def found(self) -> List[Section]:
        """Sections that were actually labelled in the document."""
        return [section for section in self.order if section is not Section.HEADER]

    def __contains__(self, section: object) -> bool:
        return bool(self._blocks.get(section))  # type: ignore[arg-type]


def split_sections(text: str) -> ResumeSections:
    """Group lines under the section header that precedes them."""
    blocks: Dict[Section, List[str]] = {}
    order: List[Section] = [Section.HEADER]
    current = Section.HEADER

    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        header = match_section_header(line)
        if header is not None:
            current = header
            if header not in order:
                order.append(header)
            blocks.setdefault(header, [])
            continue

        blocks.setdefault(current, []).append(line)

    return ResumeSections(blocks, order)


def match_section_header(line: str) -> Optional[Section]:
    """Return the section a line names, or None if it is body content.

    A header stands alone. "SKILLS" is a header; "Languages: Python, SQL" is
    not, even though it starts with a known word, because content follows the
    colon.
    """
    candidate = (line or "").strip()
    if not candidate or len(candidate.split()) > _MAX_HEADER_WORDS:
        return None

    # "SKILLS:" is a header, "Skills: Python, SQL" is a content line.
    if ":" in candidate and candidate.split(":", 1)[1].strip():
        return None

    normalized = _NON_LETTERS.sub(" ", candidate.lower())
    normalized = " ".join(normalized.split())
    if not normalized:
        return None

    for alias in _SORTED_ALIASES:
        if normalized == alias:
            return _ALIAS_LOOKUP[alias]

    return None
