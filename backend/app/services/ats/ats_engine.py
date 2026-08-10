"""Deterministic ATS scoring.

Implements docs/ats-scoring-engine.md: keyword coverage 40%, structural safety
20%, impact metrics 20%, section completeness 10%, bullet clarity 10%.

This measures the resume itself - how well an applicant tracking system can
read it and whether it carries the evidence recruiters look for. It is
deliberately not a restatement of the alignment score, which is what
`ats_score = alignment_score + 3` used to be.

Everything here is computed from data Phases 1-3 already store, so no API key
and no model call is involved and the result is reproducible.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.schemas.structured import entries

# Component weights, renormalised over whichever components have data.
WEIGHTS = {
    "keyword_coverage": 0.40,
    "structural_safety": 0.20,
    "impact_metrics": 0.20,
    "section_health": 0.10,
    "bullet_clarity": 0.10,
}

# Half the bullets carrying a measurable result is treated as full marks.
TARGET_METRIC_RATIO = 0.5

# Bullets outside this window read as either fragments or paragraphs.
MIN_BULLET_WORDS = 6
MAX_BULLET_WORDS = 45

_METRIC = re.compile(
    r"(\d+\s*%|\$\s*\d|₹\s*\d|\b\d+\s*(?:x|k|m|bn|billion|million|thousand|hours?|days?|weeks?)\b|\b\d{2,}\b)",
    re.IGNORECASE,
)

_ACTION_VERBS = frozenset("""
built designed developed implemented led managed created delivered launched
migrated automated optimised optimized improved reduced increased scaled
architected engineered shipped owned drove spearheaded established introduced
refactored integrated deployed maintained mentored coached collaborated
analysed analyzed researched authored streamlined standardised standardized
supported enabled resolved debugged tested documented coordinated
""".split())


@dataclass
class ATSResult:
    score: float = 0.0
    breakdown: Dict[str, float] = field(default_factory=dict)
    weights: Dict[str, float] = field(default_factory=dict)
    formatting_feedback: List[str] = field(default_factory=list)
    content_feedback: List[str] = field(default_factory=list)

    @property
    def warnings(self) -> List[str]:
        return self.formatting_feedback + self.content_feedback


class DeterministicATSEngine:
    def score(
        self,
        resume_data: Dict[str, Any],
        jd_data: Optional[Dict[str, Any]] = None,
        resume_text: str = "",
        extraction_meta: Optional[Dict[str, Any]] = None,
    ) -> ATSResult:
        result = ATSResult()
        components: Dict[str, float] = {}

        keyword = self._keyword_coverage(resume_data, jd_data or {}, resume_text, result)
        if keyword is not None:
            components["keyword_coverage"] = keyword

        components["structural_safety"] = self._structural_safety(extraction_meta or {}, result)
        components["impact_metrics"] = self._impact_metrics(resume_data, result)
        components["section_health"] = self._section_health(resume_data, result)

        clarity = self._bullet_clarity(resume_data, result)
        if clarity is not None:
            components["bullet_clarity"] = clarity

        result.breakdown = {name: round(value, 2) for name, value in components.items()}
        result.weights = self._renormalized_weights(components)
        result.score = round(
            sum(components[name] * result.weights[name] for name in components), 2
        )
        return result

    # --------------------------------------------------------------- components

    def _keyword_coverage(
        self,
        resume_data: Dict[str, Any],
        jd_data: Dict[str, Any],
        resume_text: str,
        result: ATSResult,
    ) -> Optional[float]:
        """Share of the JD's stated skills that appear in the resume."""
        requirements = jd_data.get("requirements", {}) or {}
        mandatory = requirements.get("normalized_mandatory") or []
        preferred = requirements.get("normalized_preferred") or []
        wanted = [str(item).lower() for item in list(mandatory) + list(preferred) if str(item).strip()]

        if not wanted:
            return None  # no JD to compare against; drop the component

        resume_skills = {
            str(skill).lower()
            for skill in (resume_data.get("skills", {}) or {}).get("normalized", [])
        }
        haystack = (resume_text or "").lower()

        present = [
            keyword for keyword in wanted
            if keyword in resume_skills or self._contains_word(haystack, keyword)
        ]
        missing = [keyword for keyword in wanted if keyword not in present]

        if missing:
            labels = self._display_names(jd_data)
            preview = ", ".join(
                sorted({labels.get(keyword, keyword) for keyword in missing})[:5]
            )
            result.content_feedback.append(
                f"{len(set(missing))} keyword(s) from the job description are absent "
                f"from your resume: {preview}."
            )

        return (len(set(present)) / len(set(wanted))) * 100.0

    def _display_names(self, jd_data: Dict[str, Any]) -> Dict[str, str]:
        """Map canonical keywords back to how the posting wrote them.

        Feedback is read by a person, so it should say "Kubernetes", not
        "kubernetes".
        """
        requirements = jd_data.get("requirements", {}) or {}
        labels: Dict[str, str] = {}
        for kind in ("mandatory", "preferred"):
            display = requirements.get(f"{kind}_skills") or []
            normalized = requirements.get(f"normalized_{kind}") or []
            for index, key in enumerate(normalized):
                if index < len(display) and display[index]:
                    labels.setdefault(str(key).lower(), str(display[index]))
        return labels

    def _structural_safety(self, extraction_meta: Dict[str, Any], result: ATSResult) -> float:
        """How cleanly a parser could read the file."""
        score = 100.0
        warnings = set(extraction_meta.get("warnings") or [])

        if extraction_meta.get("used_ocr"):
            score -= 40.0
            result.formatting_feedback.append(
                "This resume needed OCR, meaning it is image-based. Most ATS parsers "
                "cannot read it - export a text-based PDF instead."
            )
        elif extraction_meta.get("method") == "pdf_text_fallback":
            score -= 25.0
            result.formatting_feedback.append(
                "The primary parser could not read this layout cleanly. A simpler, "
                "single-column layout parses more reliably."
            )

        if "low_text_yield" in warnings or (extraction_meta.get("char_count") or 0) < 800:
            score -= 25.0
            result.formatting_feedback.append(
                "Very little text was recovered from the file, which usually means a "
                "graphics-heavy or table-based layout."
            )

        if "extraction_failed" in warnings:
            score -= 20.0
            result.formatting_feedback.append("Parts of the document could not be read.")

        if (extraction_meta.get("page_count") or 0) > 3:
            score -= 10.0
            result.formatting_feedback.append(
                "Resumes longer than three pages are often truncated by screening tools."
            )

        return max(0.0, min(100.0, score))

    def _impact_metrics(self, resume_data: Dict[str, Any], result: ATSResult) -> float:
        """Share of bullets carrying a quantified result."""
        bullets = self._all_bullets(resume_data)
        if not bullets:
            result.content_feedback.append(
                "No experience bullet points were found to evaluate for impact."
            )
            return 0.0

        with_metrics = [bullet for bullet in bullets if _METRIC.search(bullet)]
        ratio = len(with_metrics) / len(bullets)

        if ratio < TARGET_METRIC_RATIO:
            result.content_feedback.append(
                f"Only {round(ratio * 100)}% of your bullet points contain a measurable "
                "result. Add numbers - scale, percentages, time saved."
            )

        return min(100.0, (ratio / TARGET_METRIC_RATIO) * 100.0)

    def _section_health(self, resume_data: Dict[str, Any], result: ATSResult) -> float:
        personal = resume_data.get("personal_info", {}) or {}
        checks = {
            "contact details": bool(personal.get("email") or personal.get("phone")),
            "a summary": bool(resume_data.get("summary")),
            "work experience": bool(resume_data.get("experience")),
            "a skills section": bool((resume_data.get("skills", {}) or {}).get("hard_skills")),
            "education": bool(resume_data.get("education")),
        }

        missing = [name for name, present in checks.items() if not present]
        if missing:
            result.content_feedback.append(
                f"Your resume is missing {', '.join(missing)}. Screening tools expect "
                "these standard sections."
            )

        return (sum(checks.values()) / len(checks)) * 100.0

    def _bullet_clarity(self, resume_data: Dict[str, Any], result: ATSResult) -> Optional[float]:
        bullets = self._all_bullets(resume_data)
        if not bullets:
            return None

        clear = [bullet for bullet in bullets if self._is_clear(bullet)]
        ratio = len(clear) / len(bullets)

        if ratio < 0.7:
            result.content_feedback.append(
                "Several bullet points do not start with an action verb or run too long. "
                "Lead with what you did, in one line."
            )

        return ratio * 100.0

    # ------------------------------------------------------------------ helpers

    def _is_clear(self, bullet: str) -> bool:
        words = bullet.split()
        if not MIN_BULLET_WORDS <= len(words) <= MAX_BULLET_WORDS:
            return False
        first = re.sub(r"[^a-z]", "", words[0].lower())
        return first in _ACTION_VERBS

    def _all_bullets(self, resume_data: Dict[str, Any]) -> List[str]:
        bullets: List[str] = []
        for key in ("experience", "projects"):
            for entry in entries(resume_data, key):
                bullets.extend(str(item) for item in entry.get("highlights") or [])
        return [bullet for bullet in bullets if bullet and bullet.strip()]

    def _contains_word(self, haystack: str, needle: str) -> bool:
        if not needle:
            return False
        return re.search(rf"(?<![\w+#]){re.escape(needle)}(?![\w+#])", haystack) is not None

    def _renormalized_weights(self, components: Dict[str, float]) -> Dict[str, float]:
        """Spread the weight of any dropped component across the rest.

        A component with no data (no JD to compare keywords against, no bullets
        to judge) must not be scored as a zero.
        """
        total = sum(WEIGHTS[name] for name in components)
        if total <= 0:
            return {name: 0.0 for name in components}
        return {name: round(WEIGHTS[name] / total, 4) for name in components}
