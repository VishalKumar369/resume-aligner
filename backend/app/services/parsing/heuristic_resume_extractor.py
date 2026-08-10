"""Deterministic resume extractor.

This is the guaranteed floor: it needs no API key and always produces a valid
`ResumeStructuredData`. The LLM extractor sits on top of it and falls back to
it on any failure, so its quality sets the worst case for the whole product.
"""

import re
from typing import Dict, List, Optional, Tuple

from app.schemas.structured import (
    CertificationEntry,
    ContactLinks,
    EducationEntry,
    ExperienceEntry,
    PersonalInfo,
    ProjectEntry,
    ResumeStructuredData,
    SkillSet,
)
from app.services.parsing.date_utils import (
    DateRange,
    find_date_range,
    strip_date_range,
    total_years,
)
from app.services.parsing.line_utils import (
    dedupe_preserving_order,
    is_bullet,
    merge_wrapped_lines,
    split_outside_parens,
    strip_bullet,
)
from app.services.parsing.sections import Section, split_sections
from app.services.parsing.skill_vocabulary import (
    find_skills,
    find_soft_skills,
    normalize_skill,
)

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE = re.compile(r"(?:\+\d{1,3}[\s-]?)?(?:\(\d{2,4}\)[\s-]?)?\d{3,5}[\s-]?\d{3,5}(?:[\s-]?\d{2,4})?")
_URL = re.compile(r"(?:https?://)?(?:www\.)?[\w-]+\.[\w.]{2,}/[\w./#?=&%+-]*", re.IGNORECASE)
_LINKEDIN = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/\S+", re.IGNORECASE)
_GITHUB = re.compile(r"(?:https?://)?(?:www\.)?github\.com/\S+", re.IGNORECASE)

# "Bengaluru, Karnataka", "San Francisco, CA", "Remote"
_LOCATION_ONLY = re.compile(
    r"(?:Remote|Hybrid|On-?site|WFH)|"
    r"(?:[A-Z][\w.]+,\s*(?:[A-Z]{2}|[A-Z][\w.]+(?:\s[A-Z][\w.]+)?))"
)

# Tokens that legitimately begin a two-word city, so "San Francisco, CA" is not
# truncated to "Francisco, CA" while "Acme Tech Bengaluru, KA" still splits
# after "Tech".
_CITY_PREFIXES = {
    "new", "san", "los", "las", "santa", "saint", "st", "port", "fort",
    "navi", "greater", "north", "south", "east", "west",
}

_CATEGORY = re.compile(r"^(?P<category>[A-Za-z][A-Za-z0-9 /&+.\-]{1,40}):\s*(?P<items>.+)$")
_TECH_STACK = re.compile(r"^(?:tech(?:nology)?\s*stack|built\s+with|technologies)\s*:\s*(?P<items>.+)$", re.IGNORECASE)
_SCORE = re.compile(r"\b(?:\d\.\d{1,2}\s*(?:/\s*\d{1,2})?\s*(?:CGPA|GPA)|(?:CGPA|GPA)\s*:?\s*\d\.\d{1,2}|\d{1,3}(?:\.\d+)?\s*%)\b", re.IGNORECASE)
_YEAR = re.compile(r"\b(19|20)\d{2}\b")
_INTERNSHIP = re.compile(r"\b(intern|internship|trainee|apprentice)\b", re.IGNORECASE)

_KNOWN_ISSUERS = (
    "AWS", "Amazon", "Microsoft", "Google", "Oracle", "Cisco", "IBM", "Coursera",
    "Udemy", "edX", "HashiCorp", "Kubernetes", "Scrum.org", "PMI", "NPTEL",
)

_TITLE_HINT = re.compile(
    r"\b(engineer|developer|scientist|analyst|manager|architect|designer|consultant|"
    r"administrator|specialist|lead|director|intern|programmer)\b",
    re.IGNORECASE,
)


class HeuristicResumeExtractor:
    """Rule-based extraction driven by section boundaries and date ranges."""

    name = "heuristic"

    def extract(self, text: str) -> ResumeStructuredData:
        sections = split_sections(text)

        experience = self._parse_experience(sections.get(Section.EXPERIENCE))
        skills = self._parse_skills(sections.get(Section.SKILLS), text)

        data = ResumeStructuredData(
            personal_info=self._parse_personal_info(sections.get(Section.HEADER), text),
            summary=self._parse_summary(sections.get(Section.SUMMARY)),
            skills=skills,
            experience=experience,
            education=self._parse_education(sections.get(Section.EDUCATION)),
            projects=self._parse_projects(sections.get(Section.PROJECTS)),
            certifications=self._parse_certifications(sections.get(Section.CERTIFICATIONS)),
            achievements=self._parse_achievements(sections.get(Section.ACHIEVEMENTS)),
            total_experience_years=self._total_experience_years(experience, sections.get(Section.EXPERIENCE)),
        )
        data.extraction_meta = {
            "extractor": self.name,
            "sections_found": [section.value for section in sections.found],
            "confidence": self._confidence(data, sections.found),
        }
        return data

    # ------------------------------------------------------------------ header

    def _parse_personal_info(self, header_lines: List[str], full_text: str) -> PersonalInfo:
        block = "\n".join(header_lines)
        # Contact details sometimes sit below the name; search the whole
        # document as a fallback but prefer the header block.
        email = self._first_match(_EMAIL, block) or self._first_match(_EMAIL, full_text)
        phone = self._find_phone(block) or self._find_phone(full_text)

        name = self._find_name(header_lines, email)
        title = self._find_title(header_lines, name)

        return PersonalInfo(
            name=name,
            title=title,
            email=email,
            phone=phone,
            location=self._find_header_location(header_lines),
            links=self._parse_links(block or full_text),
        )

    def _find_name(self, header_lines: List[str], email: Optional[str]) -> Optional[str]:
        for line in header_lines:
            candidate = line.strip()
            if not candidate or "@" in candidate or "|" in candidate:
                continue
            if _URL.search(candidate) or any(char.isdigit() for char in candidate):
                continue
            words = candidate.split()
            if 1 <= len(words) <= 5 and all(word[0].isupper() for word in words if word[:1].isalpha()):
                return candidate

        # Fall back to the local part of the email ("john.doe@" -> "John Doe").
        if email:
            local = email.split("@", 1)[0]
            parts = [part for part in re.split(r"[._-]+", local) if part.isalpha()]
            if len(parts) >= 2:
                return " ".join(part.capitalize() for part in parts)
        return None

    def _find_title(self, header_lines: List[str], name: Optional[str]) -> Optional[str]:
        for line in header_lines:
            candidate = line.strip()
            if not candidate or candidate == name or "@" in candidate:
                continue
            if _TITLE_HINT.search(candidate) and len(candidate.split()) <= 8:
                return candidate
        return None

    def _find_header_location(self, header_lines: List[str]) -> Optional[str]:
        for line in header_lines:
            _, location = self._split_location(line)
            if location:
                return location
        return None

    def _parse_links(self, text: str) -> ContactLinks:
        linkedin = self._first_match(_LINKEDIN, text)
        github = self._first_match(_GITHUB, text)

        others = [
            url for url in _URL.findall(text)
            if isinstance(url, str) and url not in {linkedin, github}
        ]
        # _URL has a group, so findall may return tuples; re-scan for full spans.
        others = [
            match.group(0)
            for match in _URL.finditer(text)
            if match.group(0) not in {linkedin, github}
            and "linkedin.com" not in match.group(0).lower()
            and "github.com" not in match.group(0).lower()
        ]

        return ContactLinks(
            linkedin=linkedin,
            github=github,
            portfolio=others[0] if others else None,
            other=dedupe_preserving_order(others[1:]),
        )

    def _find_phone(self, text: str) -> Optional[str]:
        for line in (text or "").splitlines():
            # Skip lines that are mostly dates or metrics.
            candidate = line.strip()
            if _EMAIL.search(candidate):
                candidate = _EMAIL.sub(" ", candidate)
            match = _PHONE.search(candidate)
            if match:
                digits = re.sub(r"\D", "", match.group(0))
                if 8 <= len(digits) <= 15:
                    return match.group(0).strip()
        return None

    # ----------------------------------------------------------------- summary

    def _parse_summary(self, lines: List[str]) -> Optional[str]:
        merged = merge_wrapped_lines(lines)
        text = " ".join(strip_bullet(line) for line in merged).strip()
        return text or None

    # ------------------------------------------------------------------ skills

    def _parse_skills(self, lines: List[str], full_text: str) -> SkillSet:
        merged = merge_wrapped_lines(lines)
        categories: Dict[str, List[str]] = {}
        listed: List[str] = []

        for line in merged:
            match = _CATEGORY.match(strip_bullet(line))
            if match:
                category = match.group("category").strip()
                items = split_outside_parens(match.group("items"))
                if items:
                    categories[category] = dedupe_preserving_order(items)
                    listed.extend(items)
                continue

            # An uncategorised skills line is just a comma-separated list.
            listed.extend(split_outside_parens(strip_bullet(line)))

        # Union of what the resume lists and what the vocabulary recognises
        # anywhere in the document.
        hard_skills = dedupe_preserving_order(listed + find_skills(full_text))
        normalized = dedupe_preserving_order(
            [self._canonical_form(skill) for skill in hard_skills]
        )

        return SkillSet(
            hard_skills=hard_skills,
            soft_skills=find_soft_skills(full_text),
            normalized=normalized,
            categories=categories,
        )

    def _canonical_form(self, skill: str) -> str:
        """Reduce a resume-authored skill to the form a JD can be matched against.

        "AWS (EC2, S3)" -> "aws"; "RAG (Retrieval-Augmented Generation)
        Pipelines" -> "rag"; unknown skills keep their own cleaned name.
        """
        cleaned = re.sub(r"\([^)]*\)", " ", skill)
        cleaned = " ".join(cleaned.split()).strip(" ,;-")
        if not cleaned:
            return skill.strip().lower()

        canonical = normalize_skill(cleaned)
        if canonical != cleaned:
            return canonical.lower()

        # Not an exact alias; accept an unambiguous vocabulary hit inside it.
        hits = find_skills(cleaned)
        return (hits[0] if len(hits) == 1 else cleaned).lower()

    # -------------------------------------------------------------- experience

    def _parse_experience(self, lines: List[str]) -> List[ExperienceEntry]:
        entries: List[ExperienceEntry] = []

        for header, date_range, body in self._group_dated_entries(lines):
            company, role, location = self._split_company_and_role(header, date_range)
            start, end = date_range.as_iso() if date_range else (None, None)

            entries.append(ExperienceEntry(
                company=company,
                role=role,
                location=location,
                start_date=start,
                end_date=end,
                duration_months=date_range.duration_months if date_range else None,
                is_current=bool(date_range and date_range.is_current),
                is_internship=bool(role and _INTERNSHIP.search(role)),
                highlights=[strip_bullet(line) for line in body if is_bullet(line)],
            ))

        return entries

    def _split_company_and_role(
        self, header: List[str], date_range: Optional[DateRange]
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Resolve the company/role/location trio from an entry's header lines.

        The common layout is two lines - "Company  Location" then
        "Role  Dates" - but single-line variants appear too.
        """
        if not header:
            return None, None, None

        role_line = header[-1]
        company_line = header[-2] if len(header) >= 2 else None

        role = strip_date_range(role_line) or None
        location = None

        if company_line:
            company, location = self._split_location(company_line)
        else:
            # One-line entry: "Acme Corp - Senior Engineer, 2020-2023"
            company, role = self._split_single_line(role)

        return company, role, location

    def _split_single_line(self, text: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        if not text:
            return None, None
        for separator in (" - ", " | ", ", "):
            if separator in text:
                left, right = text.split(separator, 1)
                # The half naming a job title is the role.
                if _TITLE_HINT.search(right):
                    return left.strip() or None, right.strip() or None
                if _TITLE_HINT.search(left):
                    return right.strip() or None, left.strip() or None
        return text.strip() or None, None

    def _split_location(self, line: str) -> Tuple[Optional[str], Optional[str]]:
        """Peel a trailing location off a company or institution line.

        Scans split points right to left and takes the first that parses, so
        "Acme Tech Bengaluru, Karnataka" keeps "Acme Tech" as the company and
        "Institute of Tech, Dharwad Dharwad, Karnataka" is not double-counted.
        """
        candidate = (line or "").strip()
        tokens = candidate.split()

        for index in range(len(tokens) - 1, 0, -1):
            suffix = " ".join(tokens[index:])
            if not _LOCATION_ONLY.fullmatch(suffix):
                continue

            # "San Francisco, CA" - reclaim the city's first word.
            if index - 1 >= 1 and tokens[index - 1].lower().strip(".") in _CITY_PREFIXES:
                index -= 1
                suffix = " ".join(tokens[index:])

            company = " ".join(tokens[:index]).strip(" ,|-")
            return company or None, suffix

        return candidate or None, None

    def _total_experience_years(
        self, entries: List[ExperienceEntry], raw_lines: List[str]
    ) -> float:
        ranges = [
            found for found in (find_date_range(line) for line in merge_wrapped_lines(raw_lines))
            if found is not None
        ]
        if ranges:
            return total_years(ranges)

        # No parseable dates: fall back to summed per-entry durations.
        months = sum(entry.duration_months or 0 for entry in entries)
        return round(months / 12.0, 1)

    # --------------------------------------------------------------- education

    def _parse_education(self, lines: List[str]) -> List[EducationEntry]:
        entries: List[EducationEntry] = []

        for header, date_range, body in self._group_dated_entries(lines):
            degree_line = header[-1] if header else ""
            institution_line = header[-2] if len(header) >= 2 else None

            degree = strip_date_range(degree_line) or None
            institution, location = (
                self._split_location(institution_line) if institution_line else (None, None)
            )
            if institution is None and degree:
                # Single-line entry: "B.Tech, XYZ University, 2021-2025"
                institution, degree = self._split_degree_and_institution(degree)

            entry_text = " ".join(header + body)
            score = self._first_match(_SCORE, entry_text)

            entries.append(EducationEntry(
                degree=degree,
                institution=institution,
                location=location,
                start_year=date_range.start.year if date_range and date_range.start else None,
                end_year=self._education_end_year(date_range, entry_text),
                score=score,
                highlights=[strip_bullet(line) for line in body if is_bullet(line)],
            ))

        return entries

    def _split_degree_and_institution(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        parts = [part.strip() for part in text.split(",") if part.strip()]
        if len(parts) < 2:
            return None, text.strip() or None
        for index, part in enumerate(parts):
            if re.search(r"\b(university|college|institute|school|academy)\b", part, re.IGNORECASE):
                remainder = ", ".join(parts[:index] + parts[index + 1:])
                return part, remainder or None
        return None, text.strip() or None

    def _education_end_year(self, date_range: Optional[DateRange], entry_text: str) -> Optional[int]:
        if date_range and date_range.end:
            return date_range.end.year
        if date_range and date_range.is_current:
            return None
        match = _YEAR.search(entry_text)
        return int(match.group(0)) if match else None

    # ---------------------------------------------------------------- projects

    def _parse_projects(self, lines: List[str]) -> List[ProjectEntry]:
        entries: List[ProjectEntry] = []

        for header, date_range, body in self._group_dated_entries(lines, allow_undated=True):
            if not header:
                continue

            title_line = strip_date_range(header[-1])
            name = split_outside_parens(title_line, "|")[0] if "|" in title_line else title_line
            start, end = date_range.as_iso() if date_range else (None, None)

            tech_stack: List[str] = []
            highlights: List[str] = []
            description: Optional[str] = None

            for line in body:
                stack_match = _TECH_STACK.match(line.strip())
                if stack_match:
                    tech_stack = dedupe_preserving_order(split_outside_parens(stack_match.group("items")))
                elif is_bullet(line):
                    highlights.append(strip_bullet(line))
                elif description is None:
                    description = line.strip()

            entries.append(ProjectEntry(
                name=name.strip(" |-") or None,
                description=description,
                tech_stack=tech_stack,
                links=self._find_urls(" ".join(header)),
                start_date=start,
                end_date=end,
                highlights=highlights,
            ))

        return entries

    def _find_urls(self, text: str) -> List[str]:
        return dedupe_preserving_order([match.group(0) for match in _URL.finditer(text)])

    # ---------------------------------------------------------- certifications

    def _parse_certifications(self, lines: List[str]) -> List[CertificationEntry]:
        entries: List[CertificationEntry] = []

        for line in merge_wrapped_lines(lines):
            candidate = strip_bullet(line)
            if not candidate:
                continue

            year_match = _YEAR.search(candidate)
            year = int(year_match.group(0)) if year_match else None
            name = candidate
            if year_match:
                name = candidate.replace(year_match.group(0), "").strip(" ,()|-")

            issuer = next(
                (known for known in _KNOWN_ISSUERS if re.search(rf"\b{re.escape(known)}\b", candidate, re.IGNORECASE)),
                None,
            )

            entries.append(CertificationEntry(name=name or None, issuer=issuer, year=year))

        return entries

    # ------------------------------------------------------------ achievements

    def _parse_achievements(self, lines: List[str]) -> List[str]:
        return [strip_bullet(line) for line in merge_wrapped_lines(lines) if line.strip()]

    # ------------------------------------------------------------------ shared

    def _group_dated_entries(
        self, lines: List[str], allow_undated: bool = False
    ) -> List[Tuple[List[str], Optional[DateRange], List[str]]]:
        """Chunk a section into entries anchored on their date range.

        Each entry is (header lines, date range, body lines). The dated line is
        the anchor; any preceding non-bullet lines belong to the same entry's
        header (typically the company or institution).
        """
        merged = merge_wrapped_lines(lines)
        entries: List[Tuple[List[str], Optional[DateRange], List[str]]] = []
        pending_header: List[str] = []
        current: Optional[Tuple[List[str], Optional[DateRange], List[str]]] = None

        for line in merged:
            date_range = None if is_bullet(line) else find_date_range(line)

            if date_range is not None:
                if current is not None:
                    entries.append(current)
                current = (pending_header + [line], date_range, [])
                pending_header = []
                continue

            if current is not None and (is_bullet(line) or self._belongs_to_body(line)):
                current[2].append(line)
                continue

            # An undated header line: either the start of the next entry or a
            # dateless entry of its own.
            if allow_undated and current is not None and not is_bullet(line):
                entries.append(current)
                current = ([line], None, [])
                continue

            pending_header.append(line)

        if current is not None:
            entries.append(current)
        elif pending_header and allow_undated:
            entries.append((pending_header, None, []))

        return entries

    def _belongs_to_body(self, line: str) -> bool:
        """Non-bullet detail lines such as "Tech Stack: ..." stay with the entry."""
        return bool(_TECH_STACK.match(line.strip()))

    def _first_match(self, pattern: re.Pattern, text: str) -> Optional[str]:
        match = pattern.search(text or "")
        return match.group(0) if match else None

    # -------------------------------------------------------------- confidence

    def _confidence(self, data: ResumeStructuredData, sections_found: List[Section]) -> float:
        """How much of the expected structure was actually recovered."""
        signals = [
            bool(data.personal_info.name),
            bool(data.personal_info.email),
            bool(data.skills.hard_skills),
            bool(data.experience),
            bool(data.education),
            bool(data.summary or data.projects),
            data.total_experience_years > 0 or bool(data.education),
            len(sections_found) >= 3,
        ]
        return round(sum(signals) / len(signals), 3)
