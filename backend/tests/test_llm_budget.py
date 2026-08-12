"""The LLM budget controls.

Free-tier quotas here are metered per day (Gemini reports a limit of 20 for this
project), so these are correctness concerns rather than optimisations: a wasted
call is gone until tomorrow, and a silent fallback makes results look unstable.
"""

import json

import pytest

from app.core.config import settings
from app.services.ai.cache import LLMCache, cache_key
from app.services.ai.factory import AIFactory
from app.services.optimization.engine import OptimizationEngine
from app.services.optimization.llm_bullet_rewriter import LLMBulletRewriter
from tests.test_optimization import FakeProvider, jd, resume


@pytest.fixture(autouse=True)
def clear_quota_state():
    AIFactory.reset_quota_state()
    yield
    AIFactory.reset_quota_state()


class FakeCache:
    """In-memory stand-in for the database-backed cache."""

    def __init__(self, seed=None):
        self.store = dict(seed or {})
        self.writes = 0

    async def get(self, key):
        return self.store.get(key)

    async def put(self, key, feature, payload):
        self.store[key] = payload
        self.writes += 1


class TestFeatureSwitches:
    def test_budget_defaults_to_rewriting_only(self):
        # The heuristics parse well; rewriting prose is what they cannot do.
        assert settings.LLM_FOR_BULLET_REWRITING is True
        assert settings.LLM_FOR_RESUME_EXTRACTION is False
        assert settings.LLM_FOR_JD_EXTRACTION is False
        assert settings.LLM_FOR_ALIGNMENT is False

    def test_lookup_is_case_insensitive_and_safe(self):
        assert settings.llm_enabled_for("bullet_rewriting") is True
        assert settings.llm_enabled_for("BULLET_REWRITING") is True
        assert settings.llm_enabled_for("nonexistent_feature") is False

    def test_a_disabled_feature_reports_why(self, monkeypatch):
        monkeypatch.setattr(settings, "GEMINI_API_KEY", "a-real-looking-key-value")
        monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")

        assert AIFactory.is_available("resume_extraction") is False
        assert "LLM_FOR_RESUME_EXTRACTION" in AIFactory.unavailable_reason("resume_extraction")

    def test_no_key_disables_every_feature(self, monkeypatch):
        monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
        assert AIFactory.is_available("bullet_rewriting") is False
        assert "No AI provider key" in AIFactory.unavailable_reason("bullet_rewriting")


class TestQuotaCooldown:
    def test_recognises_a_quota_rejection(self):
        class ResourceExhausted(Exception):
            pass

        assert AIFactory.note_failure(ResourceExhausted("429 quota exceeded")) is True
        assert AIFactory.in_cooldown() is True

    def test_ignores_an_unrelated_failure(self):
        # A parse error should not stop the rest of the day's calls.
        assert AIFactory.note_failure(ValueError("bad json")) is False
        assert AIFactory.in_cooldown() is False

    def test_cooldown_blocks_further_calls(self, monkeypatch):
        monkeypatch.setattr(settings, "GEMINI_API_KEY", "a-real-looking-key-value")
        monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")

        assert AIFactory.is_available("bullet_rewriting") is True
        AIFactory.note_failure(Exception("429 RESOURCE_EXHAUSTED quota"))
        assert AIFactory.is_available("bullet_rewriting") is False

    def test_cooldown_explains_itself(self):
        AIFactory.note_failure(Exception("429 quota exceeded"))
        assert "daily quota" in AIFactory.unavailable_reason("bullet_rewriting")

    def test_reset_clears_the_cooldown(self):
        AIFactory.note_failure(Exception("429 quota"))
        AIFactory.reset_quota_state()
        assert AIFactory.in_cooldown() is False


class TestCacheKeys:
    def test_same_inputs_give_the_same_key(self):
        assert cache_key("f", "a", ["b"]) == cache_key("f", "a", ["b"])

    def test_different_inputs_give_different_keys(self):
        assert cache_key("f", "a") != cache_key("f", "b")
        assert cache_key("f", "a") != cache_key("g", "a")

    def test_rewrite_fingerprint_tracks_the_bullets(self):
        rewriter = LLMBulletRewriter()
        base = rewriter.cache_fingerprint(resume(), jd())

        changed = resume()
        changed["experience"][0]["highlights"][0] = "Something entirely different now."

        assert cache_key("r", *base) != cache_key("r", *rewriter.cache_fingerprint(changed, jd()))

    def test_rewrite_fingerprint_tracks_the_requirements(self):
        rewriter = LLMBulletRewriter()
        base = rewriter.cache_fingerprint(resume(), jd())
        other = rewriter.cache_fingerprint(resume(), jd(role="Principal SRE"))
        assert cache_key("r", *base) != cache_key("r", *other)

    @pytest.mark.asyncio
    async def test_cache_with_no_session_is_a_no_op(self):
        cache = LLMCache(db=None)
        await cache.put("k", "f", {"x": 1})
        assert await cache.get("k") is None


class TestEngineUsesTheCache:
    def _payload(self):
        return {"rewrites": [{"index": 0, "rewritten": "Maintained Docker containers for 40 services."}]}

    @pytest.mark.asyncio
    async def test_a_successful_rewrite_is_cached(self):
        provider = FakeProvider(json.dumps(self._payload()))
        engine = OptimizationEngine(rewriter=LLMBulletRewriter(provider=provider), use_llm=True)
        engine.cache = FakeCache()

        await engine.optimize(resume(), jd())

        assert engine.cache.writes == 1
        assert len(provider.calls) == 1

    @pytest.mark.asyncio
    async def test_a_second_run_on_the_same_inputs_spends_nothing(self):
        provider = FakeProvider(json.dumps(self._payload()))
        rewriter = LLMBulletRewriter(provider=provider)
        engine = OptimizationEngine(rewriter=rewriter, use_llm=True)
        engine.cache = FakeCache()

        first = await engine.optimize(resume(), jd())
        second = await engine.optimize(resume(), jd())

        # One model call total, and the second run still applied the rewrite.
        assert len(provider.calls) == 1
        assert first.from_cache is False
        assert second.from_cache is True
        assert second.optimized_data["experience"][0]["highlights"][0] == \
            "Maintained Docker containers for 40 services."

    @pytest.mark.asyncio
    async def test_a_cached_rewrite_is_re_verified_by_the_guard(self):
        # The stored payload is a raw model response, not a verdict, so a guard
        # change applies to cached results too.
        fabricating = {"rewrites": [{"index": 0, "rewritten": "Ran Kubernetes across 900 services."}]}
        engine = OptimizationEngine(rewriter=LLMBulletRewriter(), use_llm=True)
        engine.cache = FakeCache()
        key = cache_key(
            "bullet_rewriting",
            *engine.rewriter.cache_fingerprint(resume(), jd()),
        )
        engine.cache.store[key] = fabricating

        result = await engine.optimize(resume(), jd())

        assert result.from_cache is True
        assert result.rejected_rewrites
        assert "Kubernetes" not in result.optimized_data["experience"][0]["highlights"][0]

    @pytest.mark.asyncio
    async def test_a_cache_hit_needs_no_provider_at_all(self):
        # Proves the cached path never touches the network.
        engine = OptimizationEngine(rewriter=LLMBulletRewriter(provider=None), use_llm=True)
        engine.cache = FakeCache()
        key = cache_key("bullet_rewriting", *engine.rewriter.cache_fingerprint(resume(), jd()))
        engine.cache.store[key] = self._payload()

        result = await engine.optimize(resume(), jd())
        assert result.from_cache is True
        assert result.changes

    @pytest.mark.asyncio
    async def test_quota_exhaustion_is_reported_not_hidden(self):
        class Exhausted(LLMBulletRewriter):
            async def rewrite(self, resume_data, jd_data):
                raise RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded")

        engine = OptimizationEngine(rewriter=Exhausted(), use_llm=True)
        engine.cache = FakeCache()
        result = await engine.optimize(resume(), jd())

        assert result.used_llm is False
        assert "daily quota" in (result.llm_note or "")
        # And the cooldown now blocks further attempts this session.
        assert AIFactory.in_cooldown() is True
