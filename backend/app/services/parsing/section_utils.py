"""Generic labelled-section splitting, shared by the resume and JD parsers.

Both documents are written as labelled blocks; only the vocabulary of labels
differs. The matching rules - a header stands alone, content follows a colon -
are identical, so they live here once.
"""

import re
from typing import Dict, Generic, Iterable, List, Optional, Tuple, TypeVar

SectionT = TypeVar("SectionT")

_NON_LETTERS = re.compile(r"[^a-z& ]+")


def normalize_label(text: str) -> str:
    """Reduce a header or alias to comparable words: lowercase, letters only."""
    return " ".join(_NON_LETTERS.sub(" ", (text or "").lower()).split())


class SectionBlocks(Generic[SectionT]):
    """Line groups keyed by section, preserving document order."""

    def __init__(self, blocks: Dict[SectionT, List[str]], order: List[SectionT]):
        self._blocks = blocks
        self.order = order

    def get(self, section: SectionT) -> List[str]:
        return self._blocks.get(section, [])

    def text(self, section: SectionT) -> str:
        return "\n".join(self.get(section)).strip()

    def has(self, section: SectionT) -> bool:
        return bool(self._blocks.get(section))

    def __contains__(self, section: object) -> bool:
        return bool(self._blocks.get(section))  # type: ignore[arg-type]


class SectionMatcher(Generic[SectionT]):
    def __init__(
        self,
        aliases: Dict[SectionT, Iterable[str]],
        default_section: SectionT,
        max_header_words: int = 5,
        lead_in_cues: Optional[Dict[SectionT, Iterable[str]]] = None,
    ):
        # Aliases go through the same normalisation as the lines they are
        # matched against, so "what we're looking for" and "extra-curricular"
        # still match once punctuation is stripped.
        self._lookup = {
            normalize_label(alias): section
            for section, alias_group in aliases.items()
            for alias in alias_group
            if normalize_label(alias)
        }
        # Longest first, so "preferred qualifications" wins over "qualifications".
        self._sorted_aliases = sorted(self._lookup, key=len, reverse=True)
        self._default = default_section
        self._max_header_words = max_header_words
        # Colon lead-in cues: a full sentence that introduces a list and ends in
        # a colon is a header too ("In these roles you will be responsible for
        # X:"). Only sections given cues opt in, so other parsers are unchanged.
        # Longest-first again, so a more specific cue wins.
        self._lead_in_cues: List[Tuple[str, SectionT]] = sorted(
            (
                (normalize_label(cue), section)
                for section, cue_group in (lead_in_cues or {}).items()
                for cue in cue_group
                if normalize_label(cue)
            ),
            key=lambda pair: len(pair[0]),
            reverse=True,
        )

    def match(self, line: str) -> Optional[SectionT]:
        """Return the section a line names, or None if it is body content.

        A header stands alone. "SKILLS" is a header; "Skills: Python, SQL" is
        not, because content follows the colon.
        """
        candidate = (line or "").strip()
        if not candidate:
            return None

        if ":" in candidate and candidate.split(":", 1)[1].strip():
            return None

        normalized = normalize_label(candidate)
        if not normalized:
            return None

        # A colon lead-in sentence ("In these roles you will be responsible
        # for X:") introduces the list that follows, so it acts as a header
        # even though it is longer than a standalone label. Checked before the
        # word-count gate, which such lines would always fail.
        if candidate.endswith(":"):
            for cue, section in self._lead_in_cues:
                if cue and cue in normalized:
                    return section

        if len(candidate.split()) > self._max_header_words:
            return None

        for alias in self._sorted_aliases:
            if normalized == alias:
                return self._lookup[alias]

        return None

    def split(self, text: str) -> Tuple[Dict[SectionT, List[str]], List[SectionT]]:
        """Group lines under the section header that precedes them."""
        blocks: Dict[SectionT, List[str]] = {}
        order: List[SectionT] = [self._default]
        current = self._default

        for raw_line in (text or "").splitlines():
            line = raw_line.strip()
            if not line:
                continue

            header = self.match(line)
            if header is not None:
                current = header
                if header not in order:
                    order.append(header)
                blocks.setdefault(header, [])
                continue

            blocks.setdefault(current, []).append(line)

        return blocks, order
