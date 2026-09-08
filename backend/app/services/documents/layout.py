"""One layout definition, rendered by every exporter.

The .docx writer, the PDF writer, and the plain-text renderer all consume the
same ordered block list, so the three exports cannot drift apart.

The layout is deliberately plain: single column, standard headings, no tables,
no columns, no graphics. That is exactly what the `structural_safety` component
of the ATS score rewards, and what breaks resume parsers when absent.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence

from app.schemas.structured import entries


class BlockKind(str, Enum):
    NAME = "name"
    CONTACT = "contact"
    HEADING = "heading"
    SUBHEADING = "subheading"   # "Role - Company"
    META = "meta"               # dates, location
    PARAGRAPH = "paragraph"
    BULLET = "bullet"


@dataclass
class Block:
    kind: BlockKind
    text: str = ""
    # A right-aligned companion on the same line (dates against a role/company,
    # or a location). Renderers push it to the right margin; plain-text joins it.
    right: str = ""


# The body sections, keyed for the client's reorder / include-exclude control.
# The header (name, title, contact) is always first and is not reorderable.
SECTION_BUILDERS: Dict[str, Callable[[List["Block"], Dict[str, Any]], None]] = {}


def build_blocks(
    resume_data: Dict[str, Any], section_order: Optional[Sequence[str]] = None
) -> List[Block]:
    """The ordered block list.

    ``section_order`` picks which body sections appear and in what order (keys
    from ``SECTION_BUILDERS``). A section left out of the list is excluded; a
    section named but absent from the resume simply renders nothing. Passing
    None keeps the default order with every section.
    """
    blocks: List[Block] = []
    personal = resume_data.get("personal_info", {}) or {}

    name = str(personal.get("name") or "").strip()
    if name:
        blocks.append(Block(BlockKind.NAME, name))

    title = str(personal.get("title") or "").strip()
    if title:
        blocks.append(Block(BlockKind.CONTACT, title))

    contact = _contact_line(personal)
    if contact:
        blocks.append(Block(BlockKind.CONTACT, contact))

    order = [key for key in (section_order or DEFAULT_SECTION_ORDER) if key in SECTION_BUILDERS]
    if not order:
        order = list(DEFAULT_SECTION_ORDER)
    seen = set()
    for key in order:
        if key in seen:
            continue
        seen.add(key)
        SECTION_BUILDERS[key](blocks, resume_data)

    return blocks


# ---------------------------------------------------------------------- helpers


def _contact_line(personal: Dict[str, Any]) -> str:
    links = personal.get("links", {}) or {}
    parts = [
        personal.get("email"),
        personal.get("phone"),
        personal.get("location"),
        links.get("linkedin"),
        links.get("github"),
        links.get("portfolio"),
    ]
    return " | ".join(str(part).strip() for part in parts if str(part or "").strip())


def _add_summary(blocks: List[Block], resume_data: Dict[str, Any]) -> None:
    summary = str(resume_data.get("summary") or "").strip()
    if summary:
        blocks.append(Block(BlockKind.HEADING, "PROFESSIONAL SUMMARY"))
        blocks.append(Block(BlockKind.PARAGRAPH, summary))


def _add_skills(blocks: List[Block], resume_data: Dict[str, Any]) -> None:
    skills = resume_data.get("skills", {}) or {}
    categories = skills.get("categories") or {}
    hard_skills = skills.get("hard_skills") or []

    if not categories and not hard_skills:
        return

    blocks.append(Block(BlockKind.HEADING, "SKILLS"))

    if categories:
        for category, items in categories.items():
            listed = ", ".join(str(item) for item in items if str(item).strip())
            if listed:
                blocks.append(Block(BlockKind.PARAGRAPH, f"{category}: {listed}"))
        return

    blocks.append(Block(BlockKind.PARAGRAPH, ", ".join(str(item) for item in hard_skills)))


def _add_experience(blocks: List[Block], resume_data: Dict[str, Any]) -> None:
    experience = entries(resume_data, "experience")
    if not experience:
        return

    blocks.append(Block(BlockKind.HEADING, "WORK EXPERIENCE"))
    for entry in experience:
        company = str(entry.get("company") or "").strip()
        role = str(entry.get("role") or "").strip()
        location = str(entry.get("location") or "").strip()
        dates = _date_range(entry)

        # Line 1 (bold): company, with the location pushed right.
        # Line 2 (italic): role, with the dates pushed right.
        if company:
            blocks.append(Block(BlockKind.SUBHEADING, company, right=location))
            if role or dates:
                blocks.append(Block(BlockKind.META, role, right=dates))
        elif role or dates or location:
            blocks.append(Block(BlockKind.SUBHEADING, role, right=(dates or location)))

        for highlight in entry.get("highlights") or []:
            if str(highlight).strip():
                blocks.append(Block(BlockKind.BULLET, str(highlight).strip()))


def _add_projects(blocks: List[Block], resume_data: Dict[str, Any]) -> None:
    projects = entries(resume_data, "projects")
    if not projects:
        return

    blocks.append(Block(BlockKind.HEADING, "PROJECTS"))
    for project in projects:
        name = str(project.get("name") or "").strip()
        dates = _date_range(project)
        if name:
            blocks.append(Block(BlockKind.SUBHEADING, name, right=dates))

        stack = ", ".join(str(item) for item in project.get("tech_stack") or [])
        if stack:
            blocks.append(Block(BlockKind.META, f"Tech Stack: {stack}"))

        description = str(project.get("description") or "").strip()
        if description:
            blocks.append(Block(BlockKind.PARAGRAPH, description))

        for highlight in project.get("highlights") or []:
            if str(highlight).strip():
                blocks.append(Block(BlockKind.BULLET, str(highlight).strip()))


def _add_education(blocks: List[Block], resume_data: Dict[str, Any]) -> None:
    education = entries(resume_data, "education")
    if not education:
        return

    blocks.append(Block(BlockKind.HEADING, "EDUCATION"))
    for entry in education:
        institution = str(entry.get("institution") or "").strip()
        degree = str(entry.get("degree") or "").strip()
        location = str(entry.get("location") or "").strip()
        years = _year_range(entry)
        score = str(entry.get("score") or "").strip()
        secondary_right = " | ".join(part for part in (years, score) if part)

        # Line 1 (bold): institution, location right. Line 2 (italic): degree,
        # years/score right.
        if institution:
            blocks.append(Block(BlockKind.SUBHEADING, institution, right=location))
            if degree or secondary_right:
                blocks.append(Block(BlockKind.META, degree, right=secondary_right))
        elif degree or secondary_right:
            blocks.append(Block(BlockKind.SUBHEADING, degree, right=secondary_right))

        for highlight in entry.get("highlights") or []:
            if str(highlight).strip():
                blocks.append(Block(BlockKind.BULLET, str(highlight).strip()))


def _add_certifications(blocks: List[Block], resume_data: Dict[str, Any]) -> None:
    certifications = entries(resume_data, "certifications")
    if not certifications:
        return

    blocks.append(Block(BlockKind.HEADING, "CERTIFICATIONS"))
    for entry in certifications:
        parts = [entry.get("name"), entry.get("issuer"), entry.get("year")]
        line = ", ".join(str(part) for part in parts if part)
        if line:
            blocks.append(Block(BlockKind.BULLET, line))


def _add_achievements(blocks: List[Block], resume_data: Dict[str, Any]) -> None:
    achievements = [
        str(item).strip() for item in resume_data.get("achievements") or [] if str(item).strip()
    ]
    if not achievements:
        return

    blocks.append(Block(BlockKind.HEADING, "ACHIEVEMENTS"))
    for item in achievements:
        blocks.append(Block(BlockKind.BULLET, item))


_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _human_date(value: Any) -> str:
    """Turn a stored date into something a resume shows: ISO "2025-02" -> "Feb
    2025", "present" -> "Present", a bare year stays a year, anything else is
    passed through so a pre-formatted "February 2025" is left alone."""
    text = str(value or "").strip()
    if not text:
        return ""
    if text.lower() in ("present", "current", "now", "ongoing"):
        return "Present"
    iso = re.match(r"^(\d{4})-(\d{1,2})", text)
    if iso:
        year, month = iso.group(1), int(iso.group(2))
        return f"{_MONTHS[month - 1]} {year}" if 1 <= month <= 12 else year
    return text


def _date_range(entry: Dict[str, Any]) -> str:
    start = _human_date(entry.get("start_date"))
    end = _human_date(entry.get("end_date"))
    if start and end:
        return f"{start} – {end}"
    return start or end or ""


def _year_range(entry: Dict[str, Any]) -> str:
    start = entry.get("start_year")
    end = entry.get("end_year")
    if start and end:
        return f"{start} – {end}"
    return str(start or end or "")


# Registered after the builders exist. The order here is the sensible default
# used when the client sends none.
DEFAULT_SECTION_ORDER = (
    "summary", "skills", "experience", "projects",
    "education", "certifications", "achievements",
)

SECTION_BUILDERS.update({
    "summary": _add_summary,
    "skills": _add_skills,
    "experience": _add_experience,
    "projects": _add_projects,
    "education": _add_education,
    "certifications": _add_certifications,
    "achievements": _add_achievements,
})
