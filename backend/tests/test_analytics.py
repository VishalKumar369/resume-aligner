from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.company.insights import CompanyInsightsService, slugify
from app.services.dashboard.analytics import (
    PROBABILITY_CAVEAT,
    DashboardAnalyticsService,
    _LatestRun,
)
from app.services.learning.resources import SKILL_RESOURCES, resource_for, resources_for
from app.services.learning.roadmap_generator import LearningRoadmapService
from app.services.skill_gap.aggregator import SkillGapAggregator, cluster_by_category
from app.services.skill_gap.detector import SkillGapDetectorService


def analysis(missing, partial=None):
    return {
        "missing_skills": missing,
        "partial_skills": partial or [],
        "ats_warnings": [],
    }


def gap(skill, priority="P2", importance="mandatory"):
    return {"skill": skill, "priority": priority, "importance": importance, "weight": 1.0}


class TestSkillGapAggregator:
    def test_counts_how_many_jds_demand_each_gap(self):
        report = SkillGapAggregator().aggregate([
            analysis([gap("Kubernetes"), gap("Kafka")]),
            analysis([gap("Kubernetes")]),
            analysis([gap("Kubernetes")]),
        ])

        by_skill = {item.skill: item for item in report.gaps}
        assert by_skill["Kubernetes"].jd_count == 3
        assert by_skill["Kafka"].jd_count == 1
        assert report.jds_considered == 3

    def test_ranks_the_most_commonly_demanded_gap_first(self):
        report = SkillGapAggregator().aggregate([
            analysis([gap("Kafka", "P1")]),
            analysis([gap("Terraform", "P2")]),
            analysis([gap("Terraform", "P2")]),
            analysis([gap("Terraform", "P2")]),
        ])
        # Frequency across postings dominates; a single P1 does not outrank a
        # gap that three roles ask for.
        assert report.gaps[0].skill == "Terraform"

    def test_keeps_the_strongest_priority_seen(self):
        report = SkillGapAggregator().aggregate([
            analysis([gap("Kubernetes", "P3", "preferred")]),
            analysis([gap("Kubernetes", "P1")]),
        ])
        assert report.gaps[0].priority == "P1"
        assert report.gaps[0].mandatory is True

    def test_normalizes_aliases_into_one_gap(self):
        report = SkillGapAggregator().aggregate([
            analysis([gap("k8s")]),
            analysis([gap("Kubernetes")]),
        ])
        assert len(report.gaps) == 1
        assert report.gaps[0].skill == "Kubernetes"
        assert report.gaps[0].jd_count == 2

    def test_tolerates_gaps_stored_as_plain_strings(self):
        # Pre-Phase-4 rows stored missing_skills as a flat list of strings.
        report = SkillGapAggregator().aggregate([analysis(["Kubernetes", "Kafka"])])
        assert {item.skill for item in report.gaps} == {"Kubernetes", "Kafka"}

    def test_aggregates_partial_matches(self):
        report = SkillGapAggregator().aggregate([
            analysis([], [{"skill": "Kubernetes", "covered_by": "Docker"}]),
            analysis([], [{"skill": "Kubernetes", "covered_by": "Docker"}]),
        ])
        assert len(report.partial) == 1
        assert report.partial[0]["jd_count"] == 2

    def test_no_analyses_yields_an_empty_report(self):
        report = SkillGapAggregator().aggregate([])
        assert report.gaps == [] and report.jds_considered == 0

    def test_clusters_related_skills_together(self):
        report = SkillGapAggregator().aggregate([
            analysis([gap("Docker"), gap("Kubernetes"), gap("Kafka")])
        ])
        clusters = cluster_by_category(report.gaps)
        assert {item.skill for item in clusters["containers"]} == {"Docker", "Kubernetes"}
        assert {item.skill for item in clusters["messaging"]} == {"Kafka"}


def _jd(company, title, mandatory=None, created=None):
    return SimpleNamespace(
        id=uuid4(),
        company_name=company,
        title=title,
        created_at=created or datetime(2026, 8, 1),
        structured_data={"requirements": {"mandatory_skills": mandatory or []}},
    )


def _align(jd_id, score, missing=None, created=None):
    return SimpleNamespace(
        jd_id=jd_id,
        total_alignment_score=score,
        created_at=created or datetime(2026, 8, 1),
        analysis_data={"missing_skills": missing or []},
    )


class TestCompanySummaries:
    def test_groups_postings_by_company(self):
        acme1 = _jd("Acme", "Backend Engineer")
        acme2 = _jd("Acme", "Platform Engineer")
        globex = _jd("Globex", "ML Engineer")

        cards = CompanyInsightsService().summarize_companies([acme1, acme2, globex], [])

        by_name = {c["company"]: c for c in cards}
        assert by_name["Acme"]["jd_count"] == 2
        assert set(by_name["Acme"]["roles"]) == {"Backend Engineer", "Platform Engineer"}
        assert by_name["Globex"]["jd_count"] == 1

    def test_folds_company_name_variants_into_one_card(self):
        cards = CompanyInsightsService().summarize_companies(
            [_jd("Acme", "A"), _jd("acme", "B")], []
        )
        assert len(cards) == 1
        assert cards[0]["jd_count"] == 2

    def test_computes_best_and_average_alignment(self):
        jd = _jd("Acme", "Backend Engineer")
        aligns = [_align(jd.id, 80.0), _align(jd.id, 60.0)]

        card = CompanyInsightsService().summarize_companies([jd], aligns)[0]

        assert card["your_best_alignment"] == 80.0
        assert card["your_average_alignment"] == 70.0

    def test_surfaces_demanded_skills_and_gap_count(self):
        jd = _jd("Acme", "Backend Engineer", mandatory=["Python", "FastAPI"])
        aligns = [_align(jd.id, 70.0, missing=[gap("Kafka"), gap("Docker")])]

        card = CompanyInsightsService().summarize_companies([jd], aligns)[0]

        assert set(card["demanded_skills"]) == {"Python", "FastAPI"}
        assert card["gap_count"] == 2

    def test_surfaces_postings_with_no_company_name_as_role_cards(self):
        cards = CompanyInsightsService().summarize_companies(
            [_jd("Acme", "Backend Engineer"), _jd("", "Data Scientist"), _jd(None, "ML Engineer")], []
        )

        # The named company groups into one card; each nameless posting still
        # appears, labelled by its role and flagged so the UI links to its analysis.
        by_name = {c["company"]: c for c in cards}
        assert by_name["Acme"]["named"] is True
        assert by_name["Data Scientist"]["named"] is False
        assert by_name["Data Scientist"]["jd_count"] == 1
        assert by_name["ML Engineer"]["named"] is False
        assert len(cards) == 3

    def test_a_role_card_carries_ids_for_the_scoped_link(self):
        jd = _jd("", "Data Scientist")
        latest = _align(jd.id, 66.0)
        latest.resume_id = uuid4()
        latest.id = uuid4()

        card = CompanyInsightsService().summarize_companies([jd], [latest])[0]

        assert card["named"] is False
        assert card["jd_id"] == str(jd.id)
        assert card["resume_id"] == str(latest.resume_id)
        assert card["alignment_id"] == str(latest.id)

    def test_ranks_the_best_matching_company_first(self):
        strong = _jd("Strong", "A")
        weak = _jd("Weak", "B")
        aligns = [_align(strong.id, 90.0), _align(weak.id, 40.0)]

        cards = CompanyInsightsService().summarize_companies([weak, strong], aligns)

        assert [c["company"] for c in cards] == ["Strong", "Weak"]

    def test_a_company_with_no_runs_has_null_scores(self):
        card = CompanyInsightsService().summarize_companies([_jd("Acme", "A")], [])[0]
        assert card["your_best_alignment"] is None
        assert card["gap_count"] == 0


class TestPostingDetail:
    def test_carries_role_requirements_and_your_latest_match(self):
        jd = SimpleNamespace(
            id=uuid4(), title="Backend Engineer", url="https://x",
            created_at=datetime(2026, 8, 1),
            structured_data={
                "seniority": "senior", "location": "Remote",
                "requirements": {"mandatory_skills": ["Python"], "preferred_skills": ["Kafka"]},
            },
        )
        latest = _align(jd.id, 78.0)
        latest.ats_score = 62.0
        latest.resume_id = uuid4()
        latest.id = uuid4()

        detail = CompanyInsightsService()._posting_detail(jd, latest)

        assert detail["title"] == "Backend Engineer"
        assert detail["seniority"] == "senior"
        assert detail["mandatory_skills"] == ["Python"]
        assert detail["preferred_skills"] == ["Kafka"]
        assert detail["your_alignment"] == 78.0
        assert detail["your_ats"] == 62.0
        assert detail["resume_id"] == str(latest.resume_id)
        assert detail["alignment_id"] == str(latest.id)

    def test_a_posting_never_analyzed_has_null_match(self):
        jd = SimpleNamespace(id=uuid4(), title="Role", url=None, created_at=None, structured_data={})
        detail = CompanyInsightsService()._posting_detail(jd, None)

        assert detail["your_alignment"] is None
        assert detail["resume_id"] is None
        assert detail["mandatory_skills"] == []


class TestLearningResources:
    def test_every_resource_is_a_real_url(self):
        for skill, (title, url) in SKILL_RESOURCES.items():
            assert url.startswith("https://"), skill
            assert title.strip(), skill
            # The stub used to emit truncated placeholders like ".../..." .
            assert "..." not in url, skill

    def test_returns_nothing_for_an_unknown_skill(self):
        # Better no resource than an invented one.
        assert resource_for("Fictional Framework 9000") is None

    def test_skips_unknown_skills_without_failing(self):
        found = resources_for(["Kubernetes", "Fictional Framework 9000"])
        assert len(found) == 1
        assert found[0]["skill"] == "Kubernetes"


class TestLearningRoadmap:
    @pytest.mark.asyncio
    async def test_clusters_gaps_into_modules(self):
        report = SkillGapAggregator().aggregate([
            analysis([gap("Docker"), gap("Kubernetes"), gap("Kafka")])
        ])
        roadmap = await LearningRoadmapService().generate(report)

        modules = {module["module"]: module for module in roadmap["modules"]}
        assert "Containerisation & Orchestration" in modules
        assert set(modules["Containerisation & Orchestration"]["skills"]) == {"Docker", "Kubernetes"}

    @pytest.mark.asyncio
    async def test_teaches_a_prerequisite_before_what_needs_it(self):
        report = SkillGapAggregator().aggregate([
            analysis([gap("Kubernetes"), gap("Docker")])
        ])
        roadmap = await LearningRoadmapService().generate(report)
        skills = roadmap["modules"][0]["skills"]

        # Kubernetes on top of Docker; Docker has to come first.
        assert skills.index("Docker") < skills.index("Kubernetes")

    @pytest.mark.asyncio
    async def test_orders_a_prerequisite_module_first(self):
        report = SkillGapAggregator().aggregate([
            analysis([gap("FastAPI", "P1"), gap("FastAPI", "P1")]),
            analysis([gap("Python", "P3")]),
        ])
        roadmap = await LearningRoadmapService().generate(report)
        names = [module["module"] for module in roadmap["modules"]]

        # FastAPI is the higher priority, but Python has to be learned first.
        assert names.index("Programming Languages") < names.index("Backend Frameworks")

    @pytest.mark.asyncio
    async def test_schedules_modules_back_to_back(self):
        report = SkillGapAggregator().aggregate([
            analysis([gap("Docker"), gap("Kafka"), gap("Terraform")])
        ])
        roadmap = await LearningRoadmapService().generate(report)

        weeks = [(m["start_week"], m["end_week"]) for m in roadmap["modules"]]
        assert weeks[0][0] == 1
        for earlier, later in zip(weeks, weeks[1:]):
            assert later[0] == earlier[1] + 1

    @pytest.mark.asyncio
    async def test_no_gaps_returns_an_empty_plan_with_an_explanation(self):
        roadmap = await LearningRoadmapService().generate(SkillGapAggregator().aggregate([]))

        assert roadmap["modules"] == []
        assert roadmap["total_modules"] == 0
        assert "No skill gaps" in roadmap["note"]

    @pytest.mark.asyncio
    async def test_accepts_bare_skill_names(self):
        roadmap = await LearningRoadmapService().generate_roadmap(["Kubernetes", "Terraform"])
        assert roadmap["total_modules"] >= 1
        assert "Kubernetes" in roadmap["skills_covered"]

    @pytest.mark.asyncio
    async def test_ai_ml_concepts_carry_doc_links(self):
        report = SkillGapAggregator().aggregate([analysis([gap("LLM"), gap("NLP")])])
        roadmap = await LearningRoadmapService().generate(report)

        skills_with_docs = {r["skill"] for module in roadmap["modules"] for r in module["resources"]}
        assert {"LLM", "NLP"} <= skills_with_docs

    @pytest.mark.asyncio
    async def test_surfaces_partially_covered_skills_with_docs(self):
        report = SkillGapAggregator().aggregate([
            analysis([], [{"skill": "Kubernetes", "covered_by": "Docker"}]),
            analysis([], [{"skill": "Kubernetes", "covered_by": "Docker"}]),
        ])
        roadmap = await LearningRoadmapService().generate(report)

        partial = roadmap["partial_skills"]
        assert len(partial) == 1
        assert partial[0]["skill"] == "Kubernetes"
        assert partial[0]["covered_by"] == "Docker"
        assert partial[0]["jd_count"] == 2
        assert partial[0]["resource"]["url"].startswith("https://kubernetes.io")

    @pytest.mark.asyncio
    async def test_partial_skills_appear_even_with_no_hard_gaps(self):
        report = SkillGapAggregator().aggregate([
            analysis([], [{"skill": "Kafka", "covered_by": "RabbitMQ"}]),
        ])
        roadmap = await LearningRoadmapService().generate(report)

        assert roadmap["modules"] == []
        assert [p["skill"] for p in roadmap["partial_skills"]] == ["Kafka"]


class TestDashboardMetrics:
    def _run(self, jd_id, alignment, ats, missing=None):
        import uuid
        from datetime import datetime

        return _LatestRun(
            jd_id=jd_id or uuid.uuid4(),
            alignment_score=alignment,
            ats_score=ats,
            created_at=datetime(2026, 8, 11),
            analysis=analysis(missing or []),
        )

    def test_career_readiness_blends_alignment_and_ats(self):
        service = DashboardAnalyticsService()
        runs = [self._run(None, 80.0, 60.0)]
        # 80 * 0.65 + 60 * 0.35
        assert service._career_readiness(runs) == 73.0

    def test_career_readiness_is_zero_without_data(self):
        assert DashboardAnalyticsService()._career_readiness([]) == 0.0

    def test_interview_probability_states_its_basis_and_caveat(self):
        result = DashboardAnalyticsService()._interview_probability([self._run(None, 90.0, 90.0)])

        assert result["band"] == "Strong"
        assert result["basis"]
        # It must never present itself as a trained prediction.
        assert result["caveat"] == PROBABILITY_CAVEAT

    def test_interview_probability_bands_track_the_score(self):
        service = DashboardAnalyticsService()
        assert service._interview_probability([self._run(None, 90.0, 90.0)])["band"] == "Strong"
        assert service._interview_probability([self._run(None, 70.0, 70.0)])["band"] == "High"
        assert service._interview_probability([self._run(None, 50.0, 50.0)])["band"] == "Moderate"
        assert service._interview_probability([self._run(None, 20.0, 20.0)])["band"] == "Low"

    def test_interview_probability_is_unknown_without_data(self):
        assert DashboardAnalyticsService()._interview_probability([])["band"] == "Unknown"

    def test_latest_per_jd_keeps_only_the_newest_run(self):
        import uuid
        from datetime import datetime

        from app.models.alignment import AlignmentScore

        jd_id = uuid.uuid4()
        rows = [
            AlignmentScore(
                resume_id=uuid.uuid4(), jd_id=jd_id, total_alignment_score=80.0,
                ats_score=70.0, analysis_data={},
            ),
            AlignmentScore(
                resume_id=uuid.uuid4(), jd_id=jd_id, total_alignment_score=40.0,
                ats_score=50.0, analysis_data={},
            ),
        ]
        rows[0].created_at = datetime(2026, 8, 11)
        rows[1].created_at = datetime(2026, 8, 1)

        latest = DashboardAnalyticsService()._latest_per_jd(rows)
        # Re-scoring one JD ten times must not let it dominate the averages.
        assert len(latest) == 1
        assert latest[0].alignment_score == 80.0

    def test_improvements_name_the_most_demanded_gaps(self):
        report = SkillGapAggregator().aggregate([
            analysis([gap("Terraform", "P1")]),
            analysis([gap("Terraform", "P1")]),
        ])
        improvements = DashboardAnalyticsService()._improvements([], report)

        assert any("Terraform" in item["text"] for item in improvements)
        assert improvements[0]["priority"] == "high"


class TestSkillGapDetector:
    @pytest.mark.asyncio
    async def test_uses_the_shared_matcher_priorities(self):
        result = await SkillGapDetectorService().detect(
            {"skills": {"hard_skills": ["Docker"], "normalized": ["docker"]}},
            {"role": "Senior Kubernetes Engineer", "requirements": {
                "mandatory_skills": ["Kubernetes", "Terraform"],
                "normalized_mandatory": ["kubernetes", "terraform"],
                "preferred_skills": [], "normalized_preferred": [], "qualifications": [],
            }},
        )

        # Kubernetes is partly covered by Docker, so it is not a hard gap.
        assert "Terraform" in result.missing_skills
        assert any("Kubernetes" in item for item in result.partial_skills)
        # No more hardcoded demand_index: 92 on every row.
        assert all("priority" in row for row in result.priority_rank)

    @pytest.mark.asyncio
    async def test_bare_skill_lists_still_work(self):
        result = await SkillGapDetectorService().detect_gaps(["Python"], ["Python", "Terraform"])
        assert result.missing_skills == ["Terraform"]


class TestCompanySlug:
    def test_slugifies_company_names(self):
        assert slugify("Acme Technologies") == "acme-technologies"
        assert slugify("The Math Company (MathCo)") == "the-math-company-mathco"
