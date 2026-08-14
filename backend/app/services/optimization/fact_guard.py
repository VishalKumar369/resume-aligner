"""Verification that a rewritten bullet invents nothing.

An LLM asked to make a bullet sound more impressive will happily add a team
size, a percentage, or a technology that was never there. Prompting it not to is
not a control. This module is the control: every rewrite is diffed against its
original, and any new *fact* causes the rewrite to be discarded.

Wording may change freely. Claims may not.
"""

import re
from dataclasses import dataclass, field
from typing import List, Set

from app.services.parsing.skill_vocabulary import find_skills

# How much longer a rewrite may get before it looks like padding.
MAX_EXPANSION_RATIO = 1.8

_NUMBER = re.compile(r"\d+(?:[.,]\d+)*\s*%?")
_ACRONYM = re.compile(r"\b[A-Z][A-Z0-9]{1,}\b")
_CAPITALISED = re.compile(r"\b[A-Z][a-zA-Z0-9.&+-]{1,}\b")

# Capitalised words that carry no factual claim, so appearing anew is harmless.
_HARMLESS_CAPITALS = frozenset("""
A An The And Or But If Then When While For From Into Onto Over Under Across
About Above Below Between During Of To In On At By As Is Are Was Were Be Been
Being Have Has Had Do Does Did Will Would Can Could Should May Might Must
I We Our Their Its This That These Those Built Designed Developed Implemented
Led Managed Created Delivered Launched Migrated Automated Optimised Optimized
Improved Reduced Increased Scaled Architected Engineered Shipped Owned Drove
Spearheaded Established Introduced Refactored Integrated Deployed Maintained
Mentored Coached Collaborated Analysed Analyzed Researched Authored Streamlined
Standardised Standardized Supported Enabled Resolved Debugged Tested Documented
Coordinated Partnered Rebuilt Modernised Modernized Consolidated Simplified
""".split())


@dataclass
class GuardResult:
    accepted: bool
    violations: List[str] = field(default_factory=list)

    @property
    def reason(self) -> str:
        return "; ".join(self.violations)


class FactGuard:
    """Rejects rewrites that introduce facts absent from the original."""

    def check(self, original: str, rewritten: str) -> GuardResult:
        original = (original or "").strip()
        rewritten = (rewritten or "").strip()

        if not rewritten:
            return GuardResult(False, ["rewrite is empty"])
        if not original:
            return GuardResult(False, ["no original to compare against"])

        violations: List[str] = []

        new_numbers = self._numbers(rewritten) - self._numbers(original)
        if new_numbers:
            violations.append(f"invented figures: {', '.join(sorted(new_numbers))}")

        new_skills = self._skills(rewritten) - self._skills(original)
        if new_skills:
            violations.append(f"invented technologies: {', '.join(sorted(new_skills))}")

        new_names = self._proper_nouns(rewritten) - self._proper_nouns(original)
        if new_names:
            violations.append(f"invented names: {', '.join(sorted(new_names))}")

        if self._over_expanded(original, rewritten):
            violations.append("expanded far beyond the original")

        return GuardResult(not violations, violations)

    # ---------------------------------------------------------------- internals

    def _numbers(self, text: str) -> Set[str]:
        """Every figure in the text, normalised so "30 %" matches "30%"."""
        return {
            match.group(0).replace(" ", "").replace(",", "")
            for match in _NUMBER.finditer(text)
        }

    def _skills(self, text: str) -> Set[str]:
        return {skill.lower() for skill in find_skills(text)}

    def _proper_nouns(self, text: str) -> Set[str]:
        """Capitalised words and acronyms that could name a real thing.

        The first word of the text is skipped because sentence case capitalises
        it regardless of whether it is a name.
        """
        candidates: Set[str] = set()

        for match in _ACRONYM.finditer(text):
            candidates.add(match.group(0))

        words = text.split()
        for index, word in enumerate(words):
            cleaned = word.strip(".,;:()[]\"'")
            if index == 0 or not cleaned:
                continue
            if cleaned in _HARMLESS_CAPITALS:
                continue
            if _CAPITALISED.fullmatch(cleaned):
                candidates.add(cleaned)

        return {item.lower() for item in candidates}

    def _over_expanded(self, original: str, rewritten: str) -> bool:
        original_words = len(original.split())
        if original_words == 0:
            return False
        return len(rewritten.split()) / original_words > MAX_EXPANSION_RATIO
