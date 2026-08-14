"""One layout definition, rendered by every exporter.

The .docx writer, the PDF writer, and the plain-text renderer all consume the
same ordered block list, so the three exports cannot drift apart.

The layout is deliberately plain: single column, standard headings, no tables,
no columns, no graphics. That is exactly what the `structural_safety` component
of the ATS score rewards, and what breaks resume parsers when absent.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List

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
    text: str


def build_blocks(resume_data: Dict[str, Any]) -> List[Block]:
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

    _add_summary(blocks, resume_data)
    _add_skills(blocks, resume_data)
    _add_experience(blocks, resume_data)
    _add_projects(blocks, resume_data)
    _add_education(blocks, resume_data)
    _add_certifications(blocks, resume_data)
    _add_achievements(blocks, resume_data)

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
        heading = " - ".join(
            part for part in (entry.get("role"), entry.get("company")) if part
        )
        if heading:
            blocks.append(Block(BlockKind.SUBHEADING, str(heading)))

        meta = " | ".join(
            part for part in (_date_range(entry), entry.get("location")) if part
        )
        if meta:
            blocks.append(Block(BlockKind.META, str(meta)))

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
        if name:
            blocks.append(Block(BlockKind.SUBHEADING, name))

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
        heading = " - ".join(
            part for part in (entry.get("degree"), entry.get("institution")) if part
        )
        if heading:
            blocks.append(Block(BlockKind.SUBHEADING, str(heading)))

        meta = " | ".join(
            str(part) for part in (_year_range(entry), entry.get("location"), entry.get("score")) if part
        )
        if meta:
            blocks.append(Block(BlockKind.META, meta))

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


def _date_range(entry: Dict[str, Any]) -> str:
    start = str(entry.get("start_date") or "").strip()
    end = str(entry.get("end_date") or "").strip()
    if not start and not end:
        return ""
    return f"{start} - {end}".strip(" -") if start or end else ""


def _year_range(entry: Dict[str, Any]) -> str:
    start = entry.get("start_year")
    end = entry.get("end_year")
    if start and end:
        return f"{start} - {end}"
    return str(start or end or "")
