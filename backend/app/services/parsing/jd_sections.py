"""Split a job description into its labelled sections.

Separating REQUIREMENTS from PREFERRED is the whole point: a skill listed under
"Nice to have" must not be scored as a must-have, and nothing in the title or
company boilerplate should be read as a required skill at all.
"""

from enum import Enum
from typing import Dict, List, Optional

from app.services.parsing.section_utils import SectionBlocks, SectionMatcher


class JDSection(str, Enum):
    HEADER = "header"          # title / company / location block above the body
    ABOUT = "about"
    REQUIREMENTS = "requirements"
    PREFERRED = "preferred"
    RESPONSIBILITIES = "responsibilities"
    BENEFITS = "benefits"
    OTHER = "other"


_JD_ALIASES: Dict[JDSection, tuple] = {
    JDSection.ABOUT: (
        "about the role", "about this role", "about the job", "about us",
        "about the company", "about the team", "the role", "role overview",
        "job description", "overview", "job summary", "who we are",
        "the opportunity", "position summary",
    ),
    # Checked before ABOUT/RESPONSIBILITIES by longest-alias-first ordering.
    JDSection.REQUIREMENTS: (
        "minimum qualifications", "basic qualifications", "required qualifications",
        "what we are looking for", "what we're looking for", "what you'll need",
        "what you will need", "skills and experience", "skills & experience",
        "required skills", "requirements", "qualifications", "must have",
        "must haves", "must-haves", "your profile", "who you are",
        "required experience", "essential skills", "eligibility",
    ),
    JDSection.PREFERRED: (
        "preferred qualifications", "preferred skills", "preferred experience",
        "nice to have", "nice to haves", "nice-to-have", "nice-to-haves",
        "good to have", "bonus points", "bonus points if", "desired skills",
        "desirable", "preferred", "bonus", "pluses", "a plus",
    ),
    JDSection.RESPONSIBILITIES: (
        "key responsibilities", "core responsibilities", "responsibilities",
        "what you'll do", "what you will do", "what you'll be doing",
        "your responsibilities", "duties", "day to day", "day-to-day",
        "in this role you will", "your impact",
    ),
    JDSection.BENEFITS: (
        "what we offer", "benefits", "perks", "perks & benefits",
        "compensation", "why join us", "our offer", "we offer",
    ),
}

# JD headers run longer than resume ones ("What we're looking for").
_MATCHER: SectionMatcher = SectionMatcher(_JD_ALIASES, JDSection.HEADER, max_header_words=6)


class JDSections(SectionBlocks):
    @property
    def found(self) -> List[JDSection]:
        return [section for section in self.order if section is not JDSection.HEADER]

    @property
    def has_requirement_sections(self) -> bool:
        """Whether skills can be scoped, or the whole body must be scanned."""
        return self.has(JDSection.REQUIREMENTS) or self.has(JDSection.PREFERRED)


def split_jd_sections(text: str) -> JDSections:
    blocks, order = _MATCHER.split(text)
    return JDSections(blocks, order)


def match_jd_section_header(line: str) -> Optional[JDSection]:
    return _MATCHER.match(line)
