"""Line-level helpers shared by the resume extractors."""

import re
from typing import List

from app.services.parsing.date_utils import find_date_range

BULLET_PREFIX = "- "

_SENTENCE_END = re.compile(r"[.!?:;]['\")\]]?$")
_CATEGORY_LINE = re.compile(r"^[A-Za-z][A-Za-z0-9 /&+.\-]{1,40}:\s*\S")


def is_bullet(line: str) -> bool:
    return line.strip().startswith(BULLET_PREFIX)


def strip_bullet(line: str) -> str:
    stripped = line.strip()
    return stripped[len(BULLET_PREFIX):].strip() if is_bullet(stripped) else stripped


def merge_wrapped_lines(lines: List[str]) -> List[str]:
    """Rejoin lines the PDF layout wrapped mid-sentence.

    A PDF has no idea where a sentence ends - it breaks at the page margin. A
    line is treated as a continuation of the one above when the previous line
    stopped without terminal punctuation and the current line does not start
    something new (a bullet, a "Category:" line, or a dated role header).
    """
    merged: List[str] = []

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        if merged and _is_continuation(merged[-1], line):
            merged[-1] = f"{merged[-1]} {line}"
        else:
            merged.append(line)

    return merged


def _is_continuation(previous: str, current: str) -> bool:
    if _SENTENCE_END.search(previous):
        return False
    if is_bullet(current):
        return False
    if _CATEGORY_LINE.match(current):
        return False
    if find_date_range(current):
        return False
    # A wrapped fragment continues a thought; it does not start a new one with
    # a capitalised heading-like phrase of one or two words.
    return True


def split_outside_parens(text: str, separator: str = ",") -> List[str]:
    """Split on a separator, ignoring separators inside brackets.

    Keeps "AWS (EC2, S3)" intact instead of shredding it into "AWS (EC2" and
    "S3)".
    """
    parts: List[str] = []
    depth = 0
    current: List[str] = []

    for char in text:
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth = max(0, depth - 1)

        if char == separator and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(char)

    parts.append("".join(current).strip())
    return [part for part in parts if part]


def dedupe_preserving_order(values: List[str]) -> List[str]:
    """Case-insensitive de-duplication that keeps the first spelling seen."""
    seen = set()
    result = []
    for value in values:
        key = value.strip().lower()
        if key and key not in seen:
            seen.add(key)
            result.append(value.strip())
    return result
