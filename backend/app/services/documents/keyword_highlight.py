"""Highlight the JD's important terms where they appear in a resume.

A recruiter (and an ATS keyword pass) rewards a resume that visibly demonstrates
the role's required skills. This builds one regex from the JD's mandatory and
preferred skills and exposes it to both document paths: the in-place .docx editor
splits runs to bold matches, and the template renderer bolds the same terms.

Matching is word-boundary aware but tech-friendly: "Java" never matches inside
"JavaScript", and "C++"/".NET"/"Node.js" match as whole tokens. Longer terms are
tried first so "REST API" wins over "API".
"""

import re
from typing import Iterable, List, Optional, Pattern, Tuple

# Neither side of a match may touch these, so tokens stay whole ("Java" ∉
# "JavaScript") while "C++", "C#", ".NET", "Node.js" match as one term.
_BOUNDARY = r"[A-Za-z0-9+#.]"


def jd_keywords(jd_data: dict) -> List[str]:
    """The concrete skills a JD asks for — the terms worth highlighting."""
    requirements = (jd_data or {}).get("requirements") or {}
    terms: List[str] = []
    terms += [str(s) for s in (requirements.get("mandatory_skills") or [])]
    terms += [str(s) for s in (requirements.get("preferred_skills") or [])]
    return terms


def compile_keyword_pattern(keywords: Iterable[str]) -> Optional[Pattern]:
    """A case-insensitive alternation of the keywords, longest first.

    Returns None when there is nothing to highlight, so callers can cheaply skip.
    """
    seen = set()
    terms: List[str] = []
    for keyword in keywords or []:
        cleaned = (keyword or "").strip()
        if len(cleaned) < 2:
            continue
        lowered = cleaned.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        terms.append(cleaned)

    if not terms:
        return None

    terms.sort(key=len, reverse=True)
    body = "|".join(re.escape(term) for term in terms)
    return re.compile(rf"(?<!{_BOUNDARY})(?:{body})(?!{_BOUNDARY})", re.IGNORECASE)


def segment_text(text: str, pattern: Optional[Pattern]) -> List[Tuple[str, bool]]:
    """Split text into (chunk, is_keyword) runs in order, keeping every character.

    A pure helper both the .docx and PDF renderers use, so the two never drift.
    """
    if not text or pattern is None:
        return [(text, False)] if text else []

    segments: List[Tuple[str, bool]] = []
    position = 0
    for match in pattern.finditer(text):
        if match.start() > position:
            segments.append((text[position:match.start()], False))
        segments.append((match.group(0), True))
        position = match.end()
    if position < len(text):
        segments.append((text[position:], False))
    return segments or [(text, False)]
