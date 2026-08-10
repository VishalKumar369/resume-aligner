"""Date-range parsing for resume entries.

Resumes write dates a dozen ways ("February 2025 - Present", "May 2024 -
Aug 2024", "11/2021-07/2025", "2021 - 2025"). Turning them into real month
counts is what makes `total_experience_years` meaningful instead of the
regex guess it used to be.
"""

import re
from dataclasses import dataclass
from datetime import date
from typing import List, Optional, Tuple

_MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

_MONTH_NAMES = "|".join(sorted(_MONTHS, key=len, reverse=True))

# Non-capturing fragments, so they can be composed into range patterns without
# clashing group names.
_F_MONTH_YEAR = rf"(?:{_MONTH_NAMES})\.?\s+(?:19|20)\d{{2}}"
_F_NUMERIC_MONTH_YEAR = r"(?:0?[1-9]|1[0-2])[/-](?:19|20)\d{2}"
_F_YEAR = r"(?:19|20)\d{2}"
_F_PRESENT = r"(?:present|current(?:ly)?|now|ongoing|today|till\s+date|to\s+date)"

# Capturing versions, used to read a single token.
_MONTH_YEAR = re.compile(rf"\b(?P<month>{_MONTH_NAMES})\.?\s+(?P<year>(?:19|20)\d{{2}})\b", re.IGNORECASE)
_NUMERIC_MONTH_YEAR = re.compile(r"\b(?P<month>0?[1-9]|1[0-2])[/-](?P<year>(?:19|20)\d{2})\b")
_YEAR_ONLY = re.compile(r"\b(?P<year>(?:19|20)\d{2})\b")
_PRESENT = re.compile(rf"\b{_F_PRESENT}\b", re.IGNORECASE)

_RANGE_SEPARATOR = r"(?:\s*(?:-|–|—|to|until|through)\s*)"
_F_END = rf"(?:{_F_PRESENT}|{_F_MONTH_YEAR}|{_F_NUMERIC_MONTH_YEAR}|{_F_YEAR})"

# Richest start pattern first, so "Nov 2021 - Jul 2025" is not degraded into
# two bare years.
_RANGE_PATTERNS = [
    re.compile(rf"(?P<start>{fragment}){_RANGE_SEPARATOR}(?P<end>{_F_END})", re.IGNORECASE)
    for fragment in (_F_MONTH_YEAR, _F_NUMERIC_MONTH_YEAR, _F_YEAR)
]


@dataclass(frozen=True)
class DateRange:
    start: Optional[date]
    end: Optional[date]
    is_current: bool = False
    text: str = ""

    @property
    def duration_months(self) -> Optional[int]:
        if self.start is None:
            return None
        return max(0, months_between(self.start, self.end or _today()))

    def as_iso(self) -> Tuple[Optional[str], Optional[str]]:
        start = self.start.strftime("%Y-%m") if self.start else None
        if self.is_current:
            return start, "present"
        return start, (self.end.strftime("%Y-%m") if self.end else None)


def _today() -> date:
    return date.today()


def months_between(start: date, end: date) -> int:
    """Inclusive month count, so a single-month role counts as 1."""
    return (end.year - start.year) * 12 + (end.month - start.month) + 1


def parse_single_date(text: str) -> Optional[date]:
    """Parse one date token into the first day of its month."""
    if not text:
        return None

    match = _MONTH_YEAR.search(text)
    if match:
        return date(int(match.group("year")), _MONTHS[match.group("month").lower()], 1)

    match = _NUMERIC_MONTH_YEAR.search(text)
    if match:
        return date(int(match.group("year")), int(match.group("month")), 1)

    match = _YEAR_ONLY.search(text)
    if match:
        return date(int(match.group("year")), 1, 1)

    return None


def find_date_range(text: str) -> Optional[DateRange]:
    """Locate a start-end date range anywhere in a line."""
    if not text:
        return None

    for pattern in _RANGE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue

        start = parse_single_date(match.group("start"))
        if start is None:
            continue

        end_token = match.group("end")
        is_current = bool(_PRESENT.search(end_token))
        end = None if is_current else parse_single_date(end_token)

        if end is not None and end < start:
            # A transposed or misparsed range is worse than none.
            continue

        return DateRange(start=start, end=end, is_current=is_current, text=match.group(0).strip())

    return None


def strip_date_range(text: str) -> str:
    """Remove the date range from a line, leaving the role or degree behind."""
    found = find_date_range(text)
    if not found or not found.text:
        return (text or "").strip()
    return text.replace(found.text, "").strip(" |,-–—\t")


def total_months(ranges: List[DateRange]) -> int:
    """Total months covered, counting overlaps once.

    Concurrent roles (a job held while freelancing) must not inflate the total,
    so intervals are merged before summing.
    """
    intervals = []
    for item in ranges:
        if item.start is None:
            continue
        end = item.end or _today()
        if end >= item.start:
            intervals.append((item.start, end))

    if not intervals:
        return 0

    intervals.sort()
    merged = [intervals[0]]
    for start, end in intervals[1:]:
        last_start, last_end = merged[-1]
        # Touching months (Jan-Mar then Apr-Jun) form one continuous stretch.
        if start <= _next_month(last_end):
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))

    return sum(months_between(start, end) for start, end in merged)


def total_years(ranges: List[DateRange]) -> float:
    return round(total_months(ranges) / 12.0, 1)


def _next_month(value: date) -> date:
    return date(value.year + 1, 1, 1) if value.month == 12 else date(value.year, value.month + 1, 1)
