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
from typing import Any, Dict, List, Optional

from app.services.alignment.scorer import AlignmentScorerService
from app.services.ats.ats_scorer import ATSScorerService
from app.services.documents.writers import render_text
from app.services.optimization.bullet_advisor import BulletAdvisor
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
    llm_note: Optional[str] = None

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
        ats_scorer: Optional[ATSScorerService] = None,
        alignment_scorer: Optional[AlignmentScorerService] = None,
        use_llm: Optional[bool] = None,
    ):
        self.promoter = promoter or SkillPromoter()
        self.reorderer = reorderer or Reorderer()
        self.advisor = advisor or BulletAdvisor()
        self.rewriter = rewriter or LLMBulletRewriter()
        self.ats_scorer = ats_scorer or ATSScorerService()
        self.alignment_scorer = alignment_scorer or AlignmentScorerService(use_llm=False)
        self._use_llm = use_llm

    async def optimize(
        self,
        resume_data: Dict[str, Any],
        jd_data: Dict[str, Any],
        resume_text: str = "",
        extraction_meta: Optional[Dict[str, Any]] = None,
    ) -> OptimizationResult:
        result = OptimizationResult()

        baseline = await self._score(resume_data, jd_data, resume_text, extraction_meta)
        result.baseline_ats_score, result.baseline_alignment_score = baseline

        optimized = copy.deepcopy(resume_data)

        self._promote_skills(optimized, jd_data, result)
        rewritten_originals = await self._rewrite_bullets(optimized, jd_data, result)
        self._reorder(optimized, jd_data, result)

        result.suggestions = self.advisor.advise(optimized, jd_data, skip=rewritten_originals)
        result.optimized_data = optimized

        # The generated document is what a screener will actually read, so the
        # new scores are computed against its rendering, not the original file.
        optimized_text = render_text(optimized)
        optimized_meta = self._generated_document_meta(optimized_text)
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
        if not self._should_use_llm():
            result.llm_note = (
                "No language model is configured, so bullets were not rewritten. "
                "Suggestions are listed instead."
            )
            return set()

        try:
            rewrites = await self.rewriter.rewrite(optimized, jd_data)
        except Exception as exc:  # noqa: BLE001 - optimization must not fail on the model
            logger.warning("Bullet rewriting failed, keeping the original bullets: %s", exc)
            result.llm_note = f"Bullet rewriting was skipped: {str(exc)[:150]}"
            return set()

        result.used_llm = True
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

    def _generated_document_meta(self, text: str) -> Dict[str, Any]:
        """Extraction metadata a parser would report for the document we build.

        It is a single-column text export, so it parses cleanly by construction.
        """
        return {
            "method": "pdf_text",
            "file_type": "docx",
            "page_count": 1,
            "char_count": len(text),
            "used_ocr": False,
            "warnings": [],
        }

    def _should_use_llm(self) -> bool:
        if self._use_llm is not None:
            return self._use_llm
        return LLMBulletRewriter.is_available()
