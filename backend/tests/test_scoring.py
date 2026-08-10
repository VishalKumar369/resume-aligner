import json

import pytest

from app.services.alignment import components
from app.services.alignment.llm_enhancer import LLMAlignmentEnhancer
from app.services.alignment.scorer import COMPONENT_WEIGHTS, AlignmentScorerService
from app.services.alignment.skill_matcher import SkillMatcher
from app.services.ats.ats_engine import WEIGHTS, DeterministicATSEngine
from app.services.ats.ats_scorer import ATSScorerService


def resume(**overrides):
    data = {
        "schema_version": "1.0",
        "personal_info": {"name": "Priya Sharma", "email": "priya@example.com"},
        "summary": "Backend engineer building payment services.",
        "skills": {
            "hard_skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
            "normalized": ["python", "fastapi", "postgresql", "docker"],
            "soft_skills": [],
            "categories": {},
        },
        "experience": [{
            "company": "Globex",
            "role": "Backend Engineer",
            "start_date": "2021-01",
            "end_date": "present",
            "highlights": [
                "Built payment services handling 2000000 transactions per month.",
                "Designed REST APIs and reduced latency by 30%.",
            ],
        }],
        "education": [{"degree": "B.Tech", "institution": "NIT"}],
        "projects": [{
            "name": "StreamGuard",
            "tech_stack": ["Python", "PostgreSQL"],
            "highlights": ["Built an anomaly detector."],
        }],
        "certifications": [],
        "achievements": [],
        "total_experience_years": 4.0,
    }
    data.update(overrides)
    return data


def jd(**overrides):
    data = {
        "schema_version": "1.0",
        "role": "Senior Backend Engineer",
        "company": "Acme",
        "seniority": "senior",
        "min_experience_years": 4,
        "requirements": {
            "mandatory_skills": ["Python", "FastAPI", "Kubernetes"],
            "preferred_skills": ["Terraform"],
            "normalized_mandatory": ["python", "fastapi", "kubernetes"],
            "normalized_preferred": ["terraform"],
            "qualifications": [],
        },
        "responsibilities": [
            "Design and own backend payment services end to end",
            "Build and operate REST APIs",
        ],
        "keywords": [],
    }
    data.update(overrides)
    return data


class FakeProvider:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    async def chat_completion(self, messages, temperature: float = 0.7, json_mode: bool = False):
        self.calls.append(messages)
        return self.responses.pop(0) if self.responses else ""

    async def generate_embedding(self, text):  # pragma: no cover - unused
        raise NotImplementedError


class TestSkillMatcher:
    def test_matches_and_reports_missing_with_display_names(self):
        report = SkillMatcher().match(resume(), jd())

        assert "Python" in report.matched
        assert "FastAPI" in report.matched
        # Display names, not the lowercase canonical forms.
        assert "Terraform" in report.missing_display_names
        assert "terraform" not in report.missing_display_names

    def test_awards_partial_credit_for_a_related_tool(self):
        report = SkillMatcher().match(resume(), jd())

        partial = {item.skill: item.covered_by for item in report.partial}
        assert partial == {"Kubernetes": "Docker"}
        # Partially covered means not missing.
        assert "Kubernetes" not in report.missing_display_names

    def test_no_partial_credit_across_programming_languages(self):
        # Knowing Python says little about a Java role.
        report = SkillMatcher().match(
            resume(skills={"hard_skills": ["Python"], "normalized": ["python"]}),
            jd(requirements={
                "mandatory_skills": ["Java"],
                "normalized_mandatory": ["java"],
                "preferred_skills": [], "normalized_preferred": [], "qualifications": [],
            }),
        )
        assert report.partial == []
        assert "Java" in report.missing_display_names

    def test_a_skill_named_in_the_title_weighs_more(self):
        report = SkillMatcher().match(
            resume(skills={"hard_skills": [], "normalized": []}),
            jd(role="Senior Kubernetes Engineer", requirements={
                "mandatory_skills": ["Kubernetes", "Git"],
                "normalized_mandatory": ["kubernetes", "git"],
                "preferred_skills": [], "normalized_preferred": [], "qualifications": [],
            }),
        )
        weights = {item.skill: item.weight for item in report.missing}
        assert weights["Kubernetes"] > weights["Git"]

    def test_gap_priority_ranks_critical_first(self):
        report = SkillMatcher().match(
            resume(skills={"hard_skills": [], "normalized": []}),
            jd(role="Senior Kubernetes Engineer", requirements={
                "mandatory_skills": ["Kubernetes", "Git"],
                "preferred_skills": ["Terraform"],
                "normalized_mandatory": ["kubernetes", "git"],
                "normalized_preferred": ["terraform"],
                "qualifications": [],
            }),
        )
        priorities = [item.priority for item in report.missing]
        assert priorities == ["P1", "P2", "P3"]

    def test_preferred_skills_add_but_never_subtract(self):
        without = SkillMatcher().match(resume(), jd(requirements={
            "mandatory_skills": ["Python"], "normalized_mandatory": ["python"],
            "preferred_skills": [], "normalized_preferred": [], "qualifications": [],
        }))
        unmatched_preferred = SkillMatcher().match(resume(), jd(requirements={
            "mandatory_skills": ["Python"], "normalized_mandatory": ["python"],
            "preferred_skills": ["Terraform"], "normalized_preferred": ["terraform"],
            "qualifications": [],
        }))
        matched_preferred = SkillMatcher().match(resume(), jd(requirements={
            "mandatory_skills": ["Python"], "normalized_mandatory": ["python"],
            "preferred_skills": ["Docker"], "normalized_preferred": ["docker"],
            "qualifications": [],
        }))

        # Missing a nice-to-have costs nothing; having one is a bonus.
        assert unmatched_preferred.score == without.score
        assert matched_preferred.score >= without.score

    def test_reports_nothing_to_match_when_the_jd_has_no_requirements(self):
        report = SkillMatcher().match(resume(), jd(requirements={}))
        assert report.has_requirements is False
        assert report.score == 0.0


class TestATSEngine:
    def test_documented_weights_sum_to_one(self):
        assert round(sum(WEIGHTS.values()), 6) == 1.0

    def test_scores_the_five_documented_components(self):
        result = DeterministicATSEngine().score(
            resume_data=resume(), jd_data=jd(), resume_text="Python FastAPI PostgreSQL",
            extraction_meta={"method": "pdf_text", "char_count": 3000, "page_count": 1, "warnings": []},
        )
        assert set(result.breakdown) == set(WEIGHTS)
        assert 0.0 <= result.score <= 100.0

    def test_penalises_an_image_based_resume(self):
        meta = {"method": "ocr", "used_ocr": True, "char_count": 3000, "page_count": 1, "warnings": []}
        result = DeterministicATSEngine().score(resume(), jd(), "text", meta)

        assert result.breakdown["structural_safety"] <= 60
        assert any("OCR" in item or "image-based" in item for item in result.formatting_feedback)

    def test_clean_extraction_scores_full_structural_safety(self):
        meta = {"method": "pdf_text", "char_count": 3000, "page_count": 1, "warnings": []}
        result = DeterministicATSEngine().score(resume(), jd(), "text", meta)
        assert result.breakdown["structural_safety"] == 100.0

    def test_rewards_quantified_bullets(self):
        quantified = DeterministicATSEngine().score(resume(), jd(), "", {})
        vague = DeterministicATSEngine().score(
            resume(experience=[{"role": "Engineer", "highlights": [
                "Worked on the backend.", "Helped the team with things.",
            ]}]),
            jd(), "", {},
        )
        assert quantified.breakdown["impact_metrics"] > vague.breakdown["impact_metrics"]

    def test_missing_sections_reduce_section_health(self):
        stripped = resume(summary=None, education=[])
        result = DeterministicATSEngine().score(stripped, jd(), "", {})

        assert result.breakdown["section_health"] < 100.0
        assert any("missing" in item for item in result.content_feedback)

    def test_keyword_component_is_dropped_when_there_is_no_jd(self):
        result = DeterministicATSEngine().score(resume(), None, "", {})

        assert "keyword_coverage" not in result.breakdown
        # The dropped weight is redistributed, never scored as zero.
        assert round(sum(result.weights.values()), 4) == 1.0

    def test_scorer_service_exposes_the_legacy_schema(self):
        result = ATSScorerService().compute(resume(), jd(), "Python", {})
        schema = ATSScorerService().to_schema(result)

        assert schema.score == result.score
        assert schema.breakdown == result.breakdown

    @pytest.mark.asyncio
    async def test_llm_feedback_cannot_change_the_score(self):
        extra = json.dumps({
            "formatting_feedback": ["Use a single column."],
            "content_feedback": ["Quantify the second bullet."],
        })
        service = ATSScorerService(provider=FakeProvider(extra))

        deterministic = service.compute(resume(), jd(), "Python", {})
        enriched = await service.compute_with_feedback(resume(), jd(), "Python", "jd text", {})

        assert enriched.score == deterministic.score
        assert "Use a single column." in enriched.formatting_feedback

    @pytest.mark.asyncio
    async def test_llm_failure_leaves_the_deterministic_result_intact(self):
        class Exploding:
            async def chat_completion(self, messages, temperature: float = 0.7, json_mode: bool = False):
                raise RuntimeError("provider exploded")

        service = ATSScorerService(provider=Exploding())
        result = await service.compute_with_feedback(resume(), jd(), "Python", "jd", {})
        assert result.score > 0


class TestComponents:
    def test_responsibility_overlap_rewards_shared_substance(self):
        aligned = components.responsibility_overlap(resume(), jd())
        unrelated = components.responsibility_overlap(resume(), jd(responsibilities=[
            "Operate service mesh and observability tooling for global clusters",
            "Run incident response and disaster recovery drills",
        ]))
        assert aligned > unrelated

    def test_responsibility_overlap_is_unavailable_without_inputs(self):
        assert components.responsibility_overlap(resume(), jd(responsibilities=[])) is None
        assert components.responsibility_overlap(resume(experience=[], summary=None, projects=[]), jd()) is None

    def test_project_relevance_is_unavailable_without_projects(self):
        assert components.project_relevance(resume(projects=[]), jd()) is None

    def test_project_relevance_measures_jd_skill_coverage(self):
        assert components.project_relevance(resume(), jd()) > 0

    def test_seniority_is_full_marks_at_or_above_the_bar(self):
        assert components.seniority_match(4.0, jd(min_experience_years=4), resume()) == 100.0
        assert components.seniority_match(9.0, jd(min_experience_years=4), resume()) == 100.0

    def test_seniority_scales_below_the_bar(self):
        assert components.seniority_match(2.0, jd(min_experience_years=4), resume()) == 50.0

    def test_seniority_falls_back_to_bands_without_a_stated_minimum(self):
        score = components.seniority_match(6.0, jd(min_experience_years=None, seniority="senior"), resume())
        assert score == 100.0

    def test_seniority_is_unavailable_when_the_jd_states_neither(self):
        assert components.seniority_match(4.0, jd(min_experience_years=None, seniority=None), resume()) is None


class TestAlignmentScorer:
    @pytest.mark.asyncio
    async def test_uses_the_documented_component_weights(self):
        result = await AlignmentScorerService(use_llm=False).score_resume_to_jd(resume(), jd())

        assert set(result.breakdown) == set(COMPONENT_WEIGHTS)
        assert result.component_weights == {name: round(weight, 4) for name, weight in COMPONENT_WEIGHTS.items()}

    @pytest.mark.asyncio
    async def test_a_missing_component_renormalizes_instead_of_scoring_zero(self):
        no_projects = await AlignmentScorerService(use_llm=False).score_resume_to_jd(resume(projects=[]), jd())

        assert "project_match" not in no_projects.breakdown
        assert round(sum(no_projects.component_weights.values()), 4) == 1.0
        # Dropping a weak component must not drag the score down.
        with_projects = await AlignmentScorerService(use_llm=False).score_resume_to_jd(resume(), jd())
        assert no_projects.alignment_score >= with_projects.alignment_score

    @pytest.mark.asyncio
    async def test_ats_score_is_no_longer_derived_from_alignment(self):
        # It used to be literally min(100, alignment_score + 3).
        result = await AlignmentScorerService(use_llm=False).score_resume_to_jd(
            resume(), jd(), resume_text="Python FastAPI",
            extraction_meta={"method": "pdf_text", "char_count": 3000, "page_count": 1, "warnings": []},
        )
        assert result.ats_score != round(min(100.0, result.alignment_score + 3.0), 2)
        assert result.ats_breakdown

    @pytest.mark.asyncio
    async def test_keeps_the_fields_the_existing_ui_reads(self):
        result = await AlignmentScorerService(use_llm=False).score_resume_to_jd(resume(), jd())

        assert isinstance(result.alignment_score, float)
        assert isinstance(result.ats_score, float)
        assert isinstance(result.feedback, str) and result.feedback
        assert isinstance(result.missing_keywords, list)

    @pytest.mark.asyncio
    async def test_scores_a_relevant_role_far_above_an_irrelevant_one(self):
        service = AlignmentScorerService(use_llm=False)
        good = await service.score_resume_to_jd(resume(), jd())
        bad = await service.score_resume_to_jd(resume(), jd(
            role="Principal Site Reliability Engineer",
            min_experience_years=10,
            requirements={
                "mandatory_skills": ["Kubernetes", "Terraform", "Kafka", "Jenkins"],
                "normalized_mandatory": ["kubernetes", "terraform", "kafka", "jenkins"],
                "preferred_skills": [], "normalized_preferred": [], "qualifications": [],
            },
            responsibilities=["Run incident response for global clusters"],
        ))
        assert good.alignment_score > bad.alignment_score + 30

    @pytest.mark.asyncio
    async def test_reports_nothing_to_score_when_the_jd_has_no_requirements(self):
        result = await AlignmentScorerService(use_llm=False).score_resume_to_jd(
            resume(), jd(requirements={}, responsibilities=[], min_experience_years=None, seniority=None),
        )
        assert result.alignment_score == 0.0
        assert "nothing to score" in result.feedback

    @pytest.mark.asyncio
    async def test_critical_gaps_are_named_in_the_feedback(self):
        result = await AlignmentScorerService(use_llm=False).score_resume_to_jd(
            resume(skills={"hard_skills": [], "normalized": []}),
            jd(role="Senior Kubernetes Engineer", requirements={
                "mandatory_skills": ["Kubernetes"], "normalized_mandatory": ["kubernetes"],
                "preferred_skills": [], "normalized_preferred": [], "qualifications": [],
            }),
        )
        assert "Kubernetes" in result.feedback


class TestStalePayloads:
    """Rows written before Phase 2 stored experience/projects as plain strings."""

    def _legacy(self):
        return {
            "personal_info": {"name": "Old Record", "email": "old@example.com"},
            "skills": {"hard_skills": ["Python"], "soft_skills": ["communication"]},
            "experience": ["Senior Backend Engineer"],
            "education": ["bachelor", "university"],
            "projects": ["Did a thing", "Did another thing"],
            "certifications": ["aws"],
            "experience_years": 3,
        }

    def test_components_survive_a_legacy_payload(self):
        # These used to raise AttributeError: 'str' object has no attribute 'get'.
        assert components.project_relevance(self._legacy(), jd()) is None
        components.responsibility_overlap(self._legacy(), jd())

    def test_ats_engine_survives_a_legacy_payload(self):
        result = DeterministicATSEngine().score(self._legacy(), jd(), "Python", {})
        assert 0.0 <= result.score <= 100.0

    @pytest.mark.asyncio
    async def test_scoring_a_legacy_payload_does_not_crash(self):
        result = await AlignmentScorerService(use_llm=False).score_resume_to_jd(self._legacy(), jd())
        assert 0.0 <= result.alignment_score <= 100.0

    @pytest.mark.asyncio
    async def test_legacy_experience_years_key_is_still_read(self):
        result = await AlignmentScorerService(use_llm=False).score_resume_to_jd(
            self._legacy(), jd(min_experience_years=3),
        )
        # experience_years: 3 against a 3-year bar is a full match.
        assert result.breakdown["seniority_match"] == 100.0


class TestLLMEnhancement:
    def _payload(self, score=88):
        return json.dumps({
            "responsibility_match": score,
            "feedback": "Your payments work maps closely onto this role.",
            "improvement_suggestions": ["Quantify the scale of the payment platform."],
        })

    @pytest.mark.asyncio
    async def test_enhancer_parses_a_model_response(self):
        enhancer = LLMAlignmentEnhancer(provider=FakeProvider(self._payload()))
        result = await enhancer.enhance(resume(), jd())

        assert result["responsibility_match"] == 88.0
        assert result["improvement_suggestions"]

    @pytest.mark.asyncio
    async def test_enhancer_rejects_an_out_of_range_score(self):
        enhancer = LLMAlignmentEnhancer(provider=FakeProvider(json.dumps({"responsibility_match": 900})))
        assert await enhancer.enhance(resume(), jd()) is None

    @pytest.mark.asyncio
    async def test_llm_only_moves_the_responsibility_component(self):
        service = AlignmentScorerService(
            enhancer=LLMAlignmentEnhancer(provider=FakeProvider(self._payload())),
            use_llm=True,
        )
        enhanced = await service.score_resume_to_jd(resume(), jd())
        deterministic = await AlignmentScorerService(use_llm=False).score_resume_to_jd(resume(), jd())

        assert enhanced.breakdown["responsibility_match"] == 88.0
        # Every other component is untouched by the model.
        for component in ("skill_match", "project_match", "seniority_match"):
            assert enhanced.breakdown[component] == deterministic.breakdown[component]
        assert enhanced.ats_score == deterministic.ats_score

    @pytest.mark.asyncio
    async def test_a_dead_provider_falls_back_to_the_deterministic_score(self):
        class Exploding(LLMAlignmentEnhancer):
            async def enhance(self, resume_data, jd_data):
                raise RuntimeError("provider exploded")

        service = AlignmentScorerService(enhancer=Exploding(), use_llm=True)
        result = await service.score_resume_to_jd(resume(), jd())
        deterministic = await AlignmentScorerService(use_llm=False).score_resume_to_jd(resume(), jd())

        assert result.alignment_score == deterministic.alignment_score
