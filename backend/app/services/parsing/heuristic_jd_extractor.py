"""Deterministic job-description extractor.

Skills are scoped to the sections that actually state requirements, so a term
appearing in the job title ("Senior Backend Engineer") or in company
boilerplate is never reported as a required skill.
"""

import re
from typing import List, Optional, Tuple

from app.schemas.jd_structured import JDRequirements, JDStructuredData
from app.services.parsing.jd_sections import JDSection, JDSections, split_jd_sections
from app.services.parsing.line_utils import (
    dedupe_preserving_order,
    is_bullet,
    merge_wrapped_lines,
    strip_bullet,
)
from app.services.parsing.skill_vocabulary import find_skills, normalize_skill

_LOCATION_LABEL = re.compile(r"^\s*location\s*[:\-]\s*(?P<value>.+)$", re.IGNORECASE)
_WORK_MODE = re.compile(r"\b(remote|hybrid|on-?site|work from home|wfh|in-office)\b", re.IGNORECASE)
_EMPLOYMENT_TYPE = re.compile(
    r"\b(full[\s-]?time|part[\s-]?time|contract(?:or)?|permanent|internship|intern|"
    r"freelance|temporary|consultant)\b",
    re.IGNORECASE,
)

# "5+ years", "3-5 years", "at least 4 years", "2 to 4 yrs". The unit is
# required so counts like "20+ REST APIs" are never read as experience.
_EXPERIENCE = re.compile(
    r"(?P<min>\d{1,2})\s*(?:\+|(?:\s*(?:-|–|to)\s*(?P<max>\d{1,2})))?\s*\+?\s*(?:years?|yrs?)\b",
    re.IGNORECASE,
)

_DEGREE = re.compile(
    r"\b(bachelor'?s?|master'?s?|ph\.?d|doctorate|b\.?tech|b\.?e\b|b\.?sc|m\.?tech|"
    r"m\.?sc|mba|degree|diploma|graduation)\b",
    re.IGNORECASE,
)

_SENIORITY_TERMS = (
    ("intern", ("intern", "internship", "trainee")),
    ("principal", ("principal", "distinguished")),
    ("staff", ("staff",)),
    ("lead", ("lead", "team lead", "tech lead")),
    ("senior", ("senior", "sr.", "sr ")),
    ("entry", ("junior", "jr.", "entry level", "entry-level", "graduate", "fresher")),
)

_PREFERRED_CUES = re.compile(
    r"\b(nice to have|good to have|bonus|preferred|desirable|a plus|plus if|would be great)\b",
    re.IGNORECASE,
)

_TITLE_NOUNS = (
    "engineer|developer|scientist|analyst|manager|architect|designer|consultant|"
    "administrator|specialist|lead|director|intern|programmer|officer|executive"
)
_TITLE_HINT = re.compile(rf"\b({_TITLE_NOUNS})\b", re.IGNORECASE)

# "Role: ...", "Position - ...", "Job Title: ...": the value is stated outright.
_ROLE_LABEL = re.compile(
    r"^\s*(?:job\s*title|position|role|title|designation|vacancy)\s*[:\-]\s*(?P<value>.+)$",
    re.IGNORECASE,
)

# "We are looking for a Senior Data Engineer to ...": the title trails a hiring
# cue. Bounded to a few words ending in a title noun so prose isn't swallowed.
_ROLE_CUE = re.compile(
    r"\b(?:hiring|looking\s+for|seeking|searching\s+for|recruiting|we\s+need|need|require|want)\b\s*"
    r"(?:a|an|the)?\s*"
    rf"(?P<value>(?:[A-Za-z][A-Za-z+#.]*\s+){{0,3}}(?:{_TITLE_NOUNS}))\b",
    re.IGNORECASE,
)

# "Company: ...", "Employer - ...": the company is labelled outright.
_COMPANY_LABEL = re.compile(
    r"^\s*(?:company|employer|organisation|organization|company\s*name)\s*[:\-]\s*(?P<value>.+)$",
    re.IGNORECASE,
)

# "Acme is hiring ...", "At Globex, we are looking ...". Case-sensitive on the
# name so a lowercased sentence start is not misread as a company.
_COMPANY_HIRING = re.compile(
    r"(?m)^(?:At\s+)?(?P<value>[A-Z][\w&.\-]*(?:\s+[A-Z][\w&.\-]*){0,3}?)\s*,?\s+"
    r"(?:is|are)\s+(?:looking|hiring|seeking|searching)"
)

# "About Acme" but not "About the role / About us".
_COMPANY_ABOUT = re.compile(r"\b[Aa]bout\s+(?P<value>[A-Z][\w&.\-]*(?:\s+[A-Z][\w&.\-]*){0,3})\b")
_ABOUT_STOP = frozenset({
    "the", "this", "us", "our", "you", "your", "company", "role", "job",
    "position", "team", "opportunity", "we", "what", "who",
})

_WORK_MODE_CANONICAL = {
    "work from home": "remote",
    "wfh": "remote",
    "in-office": "onsite",
    "on site": "onsite",
    "on-site": "onsite",
    "onsite": "onsite",
}


class HeuristicJDExtractor:
    name = "heuristic"

    def extract(self, text: str) -> JDStructuredData:
        sections = split_jd_sections(text)
        header_lines = self._identity_lines(sections)
        body = self._body_text(sections)

        mandatory, preferred = self._parse_skills(sections, body)
        min_years, max_years = self._parse_experience_years(sections, text)
        role = self._parse_role(text, header_lines)

        data = JDStructuredData(
            role=role,
            company=self._parse_company(text, header_lines, role),
            location=self._parse_location(header_lines),
            work_mode=self._parse_work_mode(text),
            employment_type=self._parse_employment_type(header_lines, text),
            seniority=self._parse_seniority(role, text, min_years),
            min_experience_years=min_years,
            max_experience_years=max_years,
            requirements=JDRequirements(
                mandatory_skills=mandatory,
                preferred_skills=preferred,
                normalized_mandatory=self._normalize(mandatory),
                normalized_preferred=self._normalize(preferred),
                qualifications=self._parse_qualifications(sections),
            ),
            responsibilities=self._parse_responsibilities(sections),
            keywords=dedupe_preserving_order(mandatory + preferred),
        )
        data.extraction_meta = {
            "extractor": self.name,
            "sections_found": [section.value for section in sections.found],
            "skills_scoped_to_sections": sections.has_requirement_sections,
            "confidence": self._confidence(data, sections),
        }
        return data

    # -------------------------------------------------------------------- head

    def _identity_lines(self, sections: JDSections) -> List[str]:
        """Lines that may carry the title, company, and location.

        When a posting has no section headers everything lands in the header
        block, so only the first line is eligible - the rest is prose.
        """
        header_lines = sections.get(JDSection.HEADER)
        return header_lines if sections.found else header_lines[:1]

    def _looks_like_a_title(self, line: str) -> bool:
        """A title is a short label, not a sentence."""
        candidate = line.strip()
        return bool(candidate) and len(candidate.split()) <= 10 and not candidate.endswith(".")

    def _parse_role(self, text: str, header_lines: List[str]) -> Optional[str]:
        # A labelled line states the title outright, wherever it appears.
        for line in text.splitlines()[:15]:
            labelled = _ROLE_LABEL.match(line)
            if labelled:
                return self._strip_trailing_meta(labelled.group("value"))

        # A title-shaped header line (the common structured case).
        for line in header_lines:
            candidate = strip_bullet(line)
            if _TITLE_HINT.search(candidate) and self._looks_like_a_title(candidate):
                return self._strip_trailing_meta(candidate)

        # A header line that is title-shaped even without a title noun.
        first = strip_bullet(header_lines[0]) if header_lines else ""
        if self._looks_like_a_title(first):
            return self._strip_trailing_meta(first)

        # Last, a title trailing a hiring cue in prose ("looking for a X").
        cued = _ROLE_CUE.search(text)
        return cued.group("value").strip() if cued else None

    def _parse_company(
        self, text: str, header_lines: List[str], role: Optional[str]
    ) -> Optional[str]:
        # A labelled line states the company outright, wherever it appears.
        for line in text.splitlines()[:15]:
            labelled = _COMPANY_LABEL.match(line)
            if labelled:
                return labelled.group("value").strip() or None

        # Otherwise the company sits on its own header line, often followed by
        # a location: "Acme Technologies - Bengaluru, India (Hybrid)".
        for line in header_lines:
            candidate = strip_bullet(line)
            if not candidate or candidate == role:
                continue
            if _TITLE_HINT.search(candidate) or not self._looks_like_a_title(candidate):
                continue
            company = self._split_on_separator(candidate)[0]
            company = _WORK_MODE.sub("", company)
            company = _EMPLOYMENT_TYPE.sub("", company)
            company = company.strip(" ,|-()")
            if company:
                return company

        # Prose cues: "Acme is hiring ...", then "About Acme".
        hiring = _COMPANY_HIRING.search(text)
        if hiring:
            return hiring.group("value").strip() or None
        for about in _COMPANY_ABOUT.finditer(text):
            value = about.group("value").strip()
            if value and value.split()[0].lower() not in _ABOUT_STOP:
                return value
        return None

    def _parse_location(self, header_lines: List[str]) -> Optional[str]:
        for line in header_lines:
            labelled = _LOCATION_LABEL.match(line)
            if labelled:
                return labelled.group("value").strip(" ()") or None

        for line in header_lines:
            parts = self._split_on_separator(strip_bullet(line))
            for part in parts[1:]:
                cleaned = _WORK_MODE.sub("", part)
                cleaned = _EMPLOYMENT_TYPE.sub("", cleaned).strip(" ,|-()")
                if "," in cleaned and len(cleaned.split()) <= 5:
                    return cleaned
        return None

    def _split_on_separator(self, line: str) -> List[str]:
        for separator in (" - ", " – ", " | ", " · ", ", "):
            if separator in line:
                return [part.strip() for part in line.split(separator) if part.strip()]
        return [line.strip()]

    def _strip_trailing_meta(self, line: str) -> str:
        cleaned = _EMPLOYMENT_TYPE.sub("", strip_bullet(line))
        cleaned = _WORK_MODE.sub("", cleaned)
        return cleaned.strip(" ,|-()") or line.strip()

    def _parse_work_mode(self, text: str) -> Optional[str]:
        match = _WORK_MODE.search(text or "")
        if not match:
            return None
        value = match.group(1).lower()
        return _WORK_MODE_CANONICAL.get(value, value)

    def _parse_employment_type(self, header_lines: List[str], text: str) -> Optional[str]:
        # Prefer the header, where it is stated as a fact rather than in prose.
        for source in ("\n".join(header_lines), text):
            match = _EMPLOYMENT_TYPE.search(source or "")
            if match:
                return match.group(1).replace("-", "-").title()
        return None

    def _parse_seniority(self, role: Optional[str], text: str, min_years: Optional[int]) -> Optional[str]:
        haystack = f"{role or ''}\n{text or ''}".lower()
        for level, terms in _SENIORITY_TERMS:
            if any(term in haystack for term in terms):
                return level

        if min_years is None:
            return None
        if min_years <= 1:
            return "entry"
        if min_years <= 4:
            return "mid"
        if min_years <= 8:
            return "senior"
        return "staff"

    # ------------------------------------------------------------------ skills

    def _parse_skills(self, sections: JDSections, body: str) -> Tuple[List[str], List[str]]:
        if sections.has_requirement_sections:
            mandatory = find_skills(self._requirements_text(sections))
            preferred = find_skills(sections.text(JDSection.PREFERRED))
            # A skill stated as required stays required even if it is repeated
            # under "nice to have".
            preferred = [skill for skill in preferred if skill not in mandatory]
            return mandatory, preferred

        # No recognisable sections: scan the body, then demote anything sitting
        # on a "nice to have" line. Here the cue line is the only signal there
        # is, so it wins over the untargeted body scan.
        preferred = self._skills_near_cues(body)
        mandatory = [skill for skill in find_skills(body) if skill not in preferred]
        return mandatory, preferred

    def _requirements_text(self, sections: JDSections) -> str:
        return "\n".join([
            sections.text(JDSection.REQUIREMENTS),
            sections.text(JDSection.OTHER),
        ]).strip()

    def _skills_near_cues(self, body: str) -> List[str]:
        cue_lines = [line for line in body.splitlines() if _PREFERRED_CUES.search(line)]
        return find_skills("\n".join(cue_lines))

    def _body_text(self, sections: JDSections) -> str:
        """Everything except the title/company header block.

        A posting with no headers at all lands entirely in the header block; in
        that case only the first line is treated as the title and the rest is
        body, otherwise there would be nothing to read skills from.
        """
        if not sections.found:
            header_lines = sections.get(JDSection.HEADER)
            return "\n".join(header_lines[1:]).strip()

        return "\n".join(
            "\n".join(sections.get(section))
            for section in sections.order
            if section is not JDSection.HEADER
        ).strip()

    def _normalize(self, skills: List[str]) -> List[str]:
        return dedupe_preserving_order([normalize_skill(skill).lower() for skill in skills])

    # -------------------------------------------------------------- experience

    def _parse_experience_years(
        self, sections: JDSections, text: str
    ) -> Tuple[Optional[int], Optional[int]]:
        # Requirements state the bar; prose elsewhere may mention other numbers.
        for source in (self._requirements_text(sections), text):
            match = _EXPERIENCE.search(source or "")
            if match:
                minimum = int(match.group("min"))
                maximum = int(match.group("max")) if match.group("max") else None
                if maximum is not None and maximum < minimum:
                    maximum = None
                return minimum, maximum
        return None, None

    # ---------------------------------------------------------- qualifications

    def _parse_qualifications(self, sections: JDSections) -> List[str]:
        lines = merge_wrapped_lines(
            sections.get(JDSection.REQUIREMENTS) + sections.get(JDSection.PREFERRED)
        )
        return [strip_bullet(line) for line in lines if _DEGREE.search(line)]

    # -------------------------------------------------------- responsibilities

    def _parse_responsibilities(self, sections: JDSections) -> List[str]:
        lines = merge_wrapped_lines(sections.get(JDSection.RESPONSIBILITIES))
        bullets = [strip_bullet(line) for line in lines if is_bullet(line)]
        if bullets:
            return bullets
        # Some postings write responsibilities as prose rather than bullets.
        return [line.strip() for line in lines if len(line.split()) >= 4]

    # -------------------------------------------------------------- confidence

    def _confidence(self, data: JDStructuredData, sections: JDSections) -> float:
        signals = [
            bool(data.role),
            bool(data.company),
            bool(data.requirements.mandatory_skills),
            bool(data.responsibilities),
            data.min_experience_years is not None,
            bool(data.seniority),
            sections.has_requirement_sections,
        ]
        return round(sum(signals) / len(signals), 3)
