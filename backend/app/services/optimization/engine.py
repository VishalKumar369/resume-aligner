"""Resume optimization.

Produces a tailored variant of a resume for one job description, plus an honest
account of what changed and what it did to the scores.

Order matters: bullets are rewritten before anything is reordered, because a
rewrite is applied by index and reordering would invalidate those indices.

Nothing here invents experience. Skills are only promoted when already evidenced
in the resume, and every LLM rewrite passes the fact guard before it is applied.
"""

import copy
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from app.services.ai.cache import LLMCache, cache_key
from app.services.ai.factory import AIFactory
from app.services.alignment.scorer import AlignmentScorerService
from app.services.ats.ats_scorer import ATSScorerService
from app.services.documents.writers import render_text
from app.services.optimization.bullet_advisor import BulletAdvisor
from app.services.optimization.condenser import SinglePageCondenser
from app.services.optimization.llm_bullet_rewriter import LLMBulletRewriter
from app.services.optimization.reorderer import Reorderer
from app.services.optimization.skill_promoter import SkillPromoter

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    optimized_data: Dict[str, Any] = field(default_factory=dict)
    changes: List[Dict[str, str]] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    rejected_rewrites: List[Dict[str, str]] = field(default_factory=list)

    baseline_ats_score: float = 0.0
    baseline_alignment_score: float = 0.0
    ats_score: float = 0.0
    alignment_score: float = 0.0

    used_llm: bool = False
    from_cache: bool = False
    llm_note: Optional[str] = None

    # Single-page condensing. `page_count` is the final rendered length; when a
    # single page was requested but the content could not be trimmed to fit
    # without going below each role's bullet floor, `single_page_fit` is False.
    single_page: bool = False
    page_count: int = 1
    trimmed_bullets: int = 0
    single_page_fit: bool = True
    length_note: Optional[str] = None
    # Explains why these figures can differ from the headline alignment score.
    scoring_note: str = (
        "Before and after are both scored deterministically so the change is a "
        "like-for-like comparison. The alignment score shown elsewhere may use "
        "an additional model-based component and can differ slightly."
    )

    @property
    def ats_delta(self) -> float:
        return round(self.ats_score - self.baseline_ats_score, 2)

    @property
    def alignment_delta(self) -> float:
        return round(self.alignment_score - self.baseline_alignment_score, 2)

    @property
    def change_summary(self) -> List[str]:
        return [change["description"] for change in self.changes]


class OptimizationEngine:
    def __init__(
        self,
        promoter: Optional[SkillPromoter] = None,
        reorderer: Optional[Reorderer] = None,
        advisor: Optional[BulletAdvisor] = None,
        rewriter: Optional[LLMBulletRewriter] = None,
        condenser: Optional[SinglePageCondenser] = None,
        ats_scorer: Optional[ATSScorerService] = None,
        alignment_scorer: Optional[AlignmentScorerService] = None,
        use_llm: Optional[bool] = None,
        db=None,
    ):
        self.promoter = promoter or SkillPromoter()
        self.reorderer = reorderer or Reorderer()
        self.advisor = advisor or BulletAdvisor()
        self.rewriter = rewriter or LLMBulletRewriter()
        self.condenser = condenser or SinglePageCondenser()
        self.ats_scorer = ats_scorer or ATSScorerService()
        # Scoring here is always deterministic, even when bullet rewriting uses a
        # model. The before/after pair only means something if both sides are
        # measured the same way, and an LLM-derived component varies between
        # calls - especially under free-tier rate limits, where one side can fall
        # back mid-run and silently shift the delta.
        self.alignment_scorer = alignment_scorer or AlignmentScorerService(use_llm=False)
        self._use_llm = use_llm
        self.cache = LLMCache(db)

    async def optimize(
        self,
        resume_data: Dict[str, Any],
        jd_data: Dict[str, Any],
        resume_text: str = "",
        extraction_meta: Optional[Dict[str, Any]] = None,
        single_page: bool = False,
        section_order: Optional[Sequence[str]] = None,
    ) -> OptimizationResult:
        result = OptimizationResult(single_page=single_page)

        baseline = await self._score(resume_data, jd_data, resume_text, extraction_meta)
        result.baseline_ats_score, result.baseline_alignment_score = baseline

        optimized = copy.deepcopy(resume_data)

        self._promote_skills(optimized, jd_data, result)
        rewritten_originals = await self._rewrite_bullets(optimized, jd_data, result)
        self._reorder(optimized, jd_data, result)

        # Condense last, once the strongest, most relevant bullets have already
        # been surfaced by reordering - so what gets trimmed is genuinely the
        # lowest-value tail. Scoring then runs on the trimmed document below.
        if single_page:
            self._condense_to_single_page(optimized, jd_data, result)

        result.suggestions = self.advisor.advise(optimized, jd_data, skip=rewritten_originals)
        result.optimized_data = optimized

        # The generated document is what a screener will actually read, so the
        # new scores are computed against its rendering, not the original file.
        # Honour the chosen section set so an excluded section is not scored.
        optimized_text = render_text(optimized, section_order)
        optimized_meta = self._generated_document_meta(optimized_text, result.page_count)
        result.ats_score, result.alignment_score = await self._score(
            optimized, jd_data, optimized_text, optimized_meta
        )

        return result

    # ---------------------------------------------------------------- internals

    def _promote_skills(
        self, optimized: Dict[str, Any], jd_data: Dict[str, Any], result: OptimizationResult
    ) -> None:
        promotion = self.promoter.promote(optimized, jd_data)
        skills = optimized.get("skills")
        if not isinstance(skills, dict):
            return

        skills["categories"] = promotion.categories
        skills["hard_skills"] = promotion.hard_skills
        skills["normalized"] = promotion.normalized

        if promotion.promoted:
            result.changes.append({
                "type": "skills_promoted",
                "description": (
                    "Added skills you already demonstrate but had not listed: "
                    + ", ".join(promotion.promoted)
                ),
            })

    async def _rewrite_bullets(
        self, optimized: Dict[str, Any], jd_data: Dict[str, Any], result: OptimizationResult
    ) -> set:
        key = cache_key("bullet_rewriting", *self.rewriter.cache_fingerprint(optimized, jd_data))

        # A previous run on identical bullets and requirements already paid for
        # this. Free-tier quotas are daily, so not re-spending matters.
        cached = await self.cache.get(key)
        if cached is not None:
            rewrites = self.rewriter.rebuild(cached, optimized)
            result.used_llm = True
            result.from_cache = True
            return self._apply_rewrites(optimized, rewrites, result)

        if not self._should_use_llm():
            result.llm_note = (
                AIFactory.unavailable_reason("bullet_rewriting")
                or "No language model is configured, so bullets were not rewritten."
            ) + " Suggestions are listed instead."
            return set()

        try:
            rewrites = await self.rewriter.rewrite(optimized, jd_data)
        except Exception as exc:  # noqa: BLE001 - optimization must not fail on the model
            quota = AIFactory.note_failure(exc)
            logger.warning("Bullet rewriting failed, keeping the original bullets: %s", exc)
            result.llm_note = (
                AIFactory.unavailable_reason("bullet_rewriting")
                if quota
                else f"Bullet rewriting was skipped: {str(exc)[:150]}"
            )
            return set()

        if self.rewriter.last_payload is not None:
            await self.cache.put(key, "bullet_rewriting", self.rewriter.last_payload)

        result.used_llm = True
        return self._apply_rewrites(optimized, rewrites, result)

    def _apply_rewrites(
        self, optimized: Dict[str, Any], rewrites, result: OptimizationResult
    ) -> set:
        result.rejected_rewrites = rewrites.rejected

        applied = 0
        for rewrite in rewrites.accepted:
            if self._apply_rewrite(optimized, rewrite):
                applied += 1
                result.changes.append({
                    "type": "bullet_rewritten",
                    "description": f"Rewrote a bullet for {rewrite.company or 'a role'}.",
                    "before": rewrite.original,
                    "after": rewrite.rewritten,
                })

        if rewrites.rejected:
            result.changes.append({
                "type": "rewrites_blocked",
                "description": (
                    f"Blocked {len(rewrites.rejected)} suggested rewrite(s) that would have "
                    "added details your resume does not support."
                ),
            })

        if not applied and not rewrites.rejected:
            result.llm_note = "The model did not find bullets worth rewriting."

        return rewrites.rewritten_originals

    def _apply_rewrite(self, optimized: Dict[str, Any], rewrite) -> bool:
        experience = optimized.get("experience")
        if not isinstance(experience, list) or not 0 <= rewrite.entry_index < len(experience):
            return False

        entry = experience[rewrite.entry_index]
        highlights = entry.get("highlights") if isinstance(entry, dict) else None
        if not isinstance(highlights, list) or not 0 <= rewrite.bullet_index < len(highlights):
            return False

        # Guard against the resume having shifted underneath the rewrite.
        if str(highlights[rewrite.bullet_index]).strip() != rewrite.original:
            return False

        highlights[rewrite.bullet_index] = rewrite.rewritten
        return True

    def _reorder(
        self, optimized: Dict[str, Any], jd_data: Dict[str, Any], result: OptimizationResult
    ) -> None:
        reorder = self.reorderer.apply(optimized, jd_data)
        for description in reorder.changes:
            result.changes.append({"type": "reordered", "description": description})

    def _condense_to_single_page(
        self, optimized: Dict[str, Any], jd_data: Dict[str, Any], result: OptimizationResult
    ) -> None:
        condensed = self.condenser.condense(optimized, jd_data)
        result.page_count = condensed.page_count
        result.trimmed_bullets = condensed.removed_bullets
        result.single_page_fit = condensed.fits
        result.changes.extend(condensed.changes)

        if condensed.total_removed and condensed.fits:
            # The summarizing change carries the itemised detail; keep the note short.
            result.length_note = (
                "Condensed to a single page, keeping your skills, work history, "
                "education, and the most job-relevant content."
            )
        elif not condensed.fits:
            # Should be rare: even after dropping supplementary content the core
            # resume still overflows (e.g. a very long work history).
            result.length_note = (
                f"Even after condensing, the core content still needs "
                f"{condensed.page_count} pages. Every section was kept because "
                "cutting more would remove work history or education."
            )

    async def _score(
        self,
        resume_data: Dict[str, Any],
        jd_data: Dict[str, Any],
        resume_text: str,
        extraction_meta: Optional[Dict[str, Any]],
    ) -> tuple:
        alignment = await self.alignment_scorer.score_resume_to_jd(
            resume_data, jd_data, resume_text=resume_text, extraction_meta=extraction_meta
        )
        return alignment.ats_score, alignment.alignment_score

    def _generated_document_meta(self, text: str, page_count: int = 1) -> Dict[str, Any]:
        """Extraction metadata a parser would report for the document we build.

        It is a single-column text export, so it parses cleanly by construction.
        """
        return {
            "method": "pdf_text",
            "file_type": "docx",
            "page_count": max(1, page_count),
            "char_count": len(text),
            "used_ocr": False,
            "warnings": [],
        }

    def _should_use_llm(self) -> bool:
        if self._use_llm is not None:
            return self._use_llm
        return AIFactory.is_available("bullet_rewriting")
