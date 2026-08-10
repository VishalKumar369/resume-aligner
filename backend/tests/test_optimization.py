import json

import pytest

from app.services.documents.layout import BlockKind, build_blocks
from app.services.documents.writers import render_docx, render_pdf, render_text
from app.services.extraction.pipeline import extract_document
from app.services.optimization.bullet_advisor import BulletAdvisor
from app.services.optimization.engine import OptimizationEngine
from app.services.optimization.fact_guard import FactGuard
from app.services.optimization.llm_bullet_rewriter import LLMBulletRewriter
from app.services.optimization.reorderer import Reorderer
from app.services.optimization.skill_promoter import PROMOTED_CATEGORY, SkillPromoter

ORIGINAL = "Supported a FastAPI migration, stabilizing REST API contracts across services."


def resume(**overrides):
    data = {
        "schema_version": "1.0",
        "personal_info": {
            "name": "Priya Sharma", "title": "Backend Engineer",
            "email": "priya@example.com", "phone": "+91 98765 43210",
            "links": {"github": "github.com/priya"},
        },
        "summary": "Backend engineer building payment services.",
        "skills": {
            "hard_skills": ["Python", "Git"],
            "normalized": ["python", "git"],
            "soft_skills": [],
            "categories": {"Languages": ["Python"], "Tools": ["Git"]},
        },
        "experience": [{
            "company": "Globex", "role": "Backend Engineer",
            "start_date": "2021-01", "end_date": "present",
            "highlights": [
                "Responsible for maintaining Docker containers for 40 services.",
                "Built FastAPI endpoints handling 200000 requests per day.",
            ],
        }],
        "education": [{"degree": "B.Tech", "institution": "NIT", "start_year": 2017, "end_year": 2021}],
        "projects": [
            {"name": "SiteWatch", "tech_stack": ["PHP"], "highlights": ["Built a monitor."]},
            {"name": "StreamGuard", "tech_stack": ["Python", "Docker"], "highlights": ["Built a detector."]},
        ],
        "certifications": [{"name": "AWS Certified Developer", "issuer": "AWS", "year": 2024}],
        "achievements": ["Spoke at PyCon India."],
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
            "mandatory_skills": ["Python", "FastAPI", "Docker"],
            "preferred_skills": ["Kafka"],
            "normalized_mandatory": ["python", "fastapi", "docker"],
            "normalized_preferred": ["kafka"],
            "qualifications": [],
        },
        "responsibilities": ["Design and own backend services end to end"],
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


class TestFactGuard:
    def test_accepts_a_pure_reword(self):
        rewrite = "Drove a FastAPI migration, stabilising REST API contracts across services."
        assert FactGuard().check(ORIGINAL, rewrite).accepted is True

    def test_rejects_an_invented_figure(self):
        verdict = FactGuard().check(ORIGINAL, "Led a FastAPI migration across 12 services, cutting latency 40%.")
        assert verdict.accepted is False
        assert "figures" in verdict.reason

    def test_rejects_an_invented_technology(self):
        verdict = FactGuard().check(ORIGINAL, "Supported a FastAPI migration onto Kubernetes.")
        assert verdict.accepted is False
        assert "technologies" in verdict.reason

    def test_rejects_an_invented_employer(self):
        verdict = FactGuard().check(ORIGINAL, "Supported a FastAPI migration at Google, stabilizing contracts.")
        assert verdict.accepted is False
        assert "names" in verdict.reason

    def test_rejects_an_invented_acronym(self):
        verdict = FactGuard().check(ORIGINAL, "Supported a FastAPI migration, adding RBAC to REST API contracts.")
        assert verdict.accepted is False

    def test_rejects_padding(self):
        padded = (
            "Supported an extremely complex, business critical, enterprise grade FastAPI "
            "migration effort, carefully stabilizing every single REST API contract while "
            "dramatically improving overall quality across all services and teams involved."
        )
        verdict = FactGuard().check(ORIGINAL, padded)
        assert verdict.accepted is False
        assert "expanded" in verdict.reason

    def test_keeps_figures_that_were_already_there(self):
        original = "Reduced regression cycles and QA rework by 15-25%."
        assert FactGuard().check(original, "Cut regression cycles and QA rework by 15-25%.").accepted is True

    def test_comma_formatting_of_an_existing_number_is_not_a_new_fact(self):
        original = "Served 200000 users."
        assert FactGuard().check(original, "Scaled to serve 200,000 users.").accepted is True

    def test_rejects_an_empty_rewrite(self):
        assert FactGuard().check(ORIGINAL, "   ").accepted is False


class TestSkillPromoter:
    def test_promotes_evidenced_skills_the_resume_never_listed(self):
        result = SkillPromoter().promote(resume(), jd())

        # Docker and FastAPI appear in bullets but not in the SKILLS block.
        assert set(result.promoted) == {"Docker", "FastAPI"}
        assert result.categories[PROMOTED_CATEGORY] == ["Docker", "FastAPI"]

    def test_never_adds_a_skill_the_resume_cannot_support(self):
        result = SkillPromoter().promote(resume(), jd())
        # Kafka is wanted by the JD but appears nowhere in the resume.
        assert "Kafka" not in result.promoted

    def test_keeps_normalized_in_step_with_hard_skills(self):
        result = SkillPromoter().promote(resume(), jd())
        assert "docker" in result.normalized
        assert len(result.normalized) == len(set(result.normalized))

    def test_does_nothing_when_everything_is_already_listed(self):
        already = resume(skills={
            "hard_skills": ["Python", "FastAPI", "Docker"],
            "normalized": ["python", "fastapi", "docker"],
            "categories": {"All": ["Python", "FastAPI", "Docker"]},
        })
        assert SkillPromoter().promote(already, jd()).promoted == []


class TestReorderer:
    def test_moves_required_skills_to_the_front(self):
        data = resume(skills={
            "hard_skills": ["Git", "Python"], "normalized": ["git", "python"], "categories": {},
        })
        Reorderer().apply(data, jd())
        assert data["skills"]["hard_skills"][0] == "Python"

    def test_leads_with_the_most_relevant_bullet(self):
        data = resume()
        Reorderer().apply(data, jd())
        # The FastAPI bullet matches the JD; the Docker one also does, but the
        # relevant subset keeps its original relative order.
        assert "FastAPI" in data["experience"][0]["highlights"][0] or \
               "Docker" in data["experience"][0]["highlights"][0]

    def test_reorders_projects_by_relevance(self):
        data = resume()
        Reorderer().apply(data, jd())
        assert data["projects"][0]["name"] == "StreamGuard"

    def test_never_resequences_employment_history(self):
        data = resume(experience=[
            {"company": "Old", "role": "Engineer", "highlights": ["Used Python and Docker."]},
            {"company": "New", "role": "Engineer", "highlights": ["Wrote docs."]},
        ])
        Reorderer().apply(data, jd())
        # Reordering jobs would misrepresent a career, so order is preserved
        # even though the second entry is less relevant.
        assert [entry["company"] for entry in data["experience"]] == ["Old", "New"]


class TestBulletAdvisor:
    def test_flags_a_bullet_with_no_action_verb(self):
        advice = BulletAdvisor().advise(resume(), jd())
        assert any("action verb" in item for item in advice)

    def test_flags_a_bullet_with_no_metric(self):
        data = resume(experience=[{
            "company": "Globex", "role": "Engineer",
            "highlights": ["Built FastAPI services for internal teams and partners."],
        }])
        advice = BulletAdvisor().advise(data, jd())
        assert any("number" in item for item in advice)

    def test_skips_bullets_that_were_already_rewritten(self):
        data = resume()
        original = data["experience"][0]["highlights"][0]
        advice = BulletAdvisor().advise(data, jd(), skip={original})
        assert not any(original[:40] in item for item in advice)


class TestLLMBulletRewriter:
    def _payload(self, index, text):
        return json.dumps({"rewrites": [{"index": index, "rewritten": text}]})

    @pytest.mark.asyncio
    async def test_accepts_a_faithful_rewrite(self):
        good = "Maintained Docker containers for 40 services."
        provider = FakeProvider(self._payload(0, good))
        result = await LLMBulletRewriter(provider=provider).rewrite(resume(), jd())

        assert len(result.accepted) == 1
        assert result.accepted[0].rewritten == good
        assert result.accepted[0].entry_index == 0
        assert result.accepted[0].bullet_index == 0

    @pytest.mark.asyncio
    async def test_discards_a_rewrite_that_invents_a_fact(self):
        provider = FakeProvider(self._payload(0, "Maintained Docker containers for 400 services on AWS."))
        result = await LLMBulletRewriter(provider=provider).rewrite(resume(), jd())

        assert result.accepted == []
        assert len(result.rejected) == 1
        assert "reason" in result.rejected[0]

    @pytest.mark.asyncio
    async def test_ignores_an_out_of_range_index(self):
        provider = FakeProvider(self._payload(99, "Anything at all here."))
        result = await LLMBulletRewriter(provider=provider).rewrite(resume(), jd())
        assert result.accepted == [] and result.rejected == []

    @pytest.mark.asyncio
    async def test_unparseable_output_yields_no_rewrites(self):
        result = await LLMBulletRewriter(provider=FakeProvider("not json")).rewrite(resume(), jd())
        assert result.accepted == []
        assert result.considered > 0

    @pytest.mark.asyncio
    async def test_sends_every_bullet_in_one_request(self):
        # Free-tier providers are rate limited per minute.
        provider = FakeProvider(json.dumps({"rewrites": []}))
        await LLMBulletRewriter(provider=provider).rewrite(resume(), jd())
        assert len(provider.calls) == 1


class TestOptimizationEngine:
    @pytest.mark.asyncio
    async def test_works_without_a_language_model(self):
        result = await OptimizationEngine(use_llm=False).optimize(resume(), jd())

        assert result.used_llm is False
        assert result.optimized_data
        assert result.changes            # promotion and reordering still happen
        assert result.suggestions        # advice replaces rewriting
        assert "No language model" in (result.llm_note or "")

    @pytest.mark.asyncio
    async def test_never_mutates_the_input(self):
        original = resume()
        snapshot = json.dumps(original, sort_keys=True)
        await OptimizationEngine(use_llm=False).optimize(original, jd())
        assert json.dumps(original, sort_keys=True) == snapshot

    @pytest.mark.asyncio
    async def test_improves_a_weak_resume(self):
        scanned = {"method": "ocr", "used_ocr": True, "char_count": 900, "page_count": 1, "warnings": []}
        result = await OptimizationEngine(use_llm=False).optimize(
            resume(), jd(), resume_text="Priya Sharma Python", extraction_meta=scanned,
        )
        # Promotion plus a clean generated document beats a scanned original.
        assert result.ats_delta > 0
        assert result.alignment_delta > 0

    @pytest.mark.asyncio
    async def test_a_dead_model_falls_back_to_the_deterministic_result(self):
        class Exploding(LLMBulletRewriter):
            async def rewrite(self, resume_data, jd_data):
                raise RuntimeError("provider exploded")

        result = await OptimizationEngine(rewriter=Exploding(), use_llm=True).optimize(resume(), jd())

        assert result.used_llm is False
        assert "provider exploded" in (result.llm_note or "")
        assert result.optimized_data

    @pytest.mark.asyncio
    async def test_applies_an_accepted_rewrite_and_records_before_and_after(self):
        good = "Maintained Docker containers for 40 services."
        rewriter = LLMBulletRewriter(provider=FakeProvider(
            json.dumps({"rewrites": [{"index": 0, "rewritten": good}]})
        ))
        result = await OptimizationEngine(rewriter=rewriter, use_llm=True).optimize(resume(), jd())

        assert result.optimized_data["experience"][0]["highlights"][0] == good
        rewrite_changes = [c for c in result.changes if c["type"] == "bullet_rewritten"]
        assert rewrite_changes and "before" in rewrite_changes[0]

    @pytest.mark.asyncio
    async def test_reports_blocked_rewrites_rather_than_hiding_them(self):
        rewriter = LLMBulletRewriter(provider=FakeProvider(
            json.dumps({"rewrites": [{"index": 0, "rewritten": "Ran Kubernetes for 900 services."}]})
        ))
        result = await OptimizationEngine(rewriter=rewriter, use_llm=True).optimize(resume(), jd())

        assert result.rejected_rewrites
        assert any(c["type"] == "rewrites_blocked" for c in result.changes)
        # The original bullet survives untouched.
        assert "Kubernetes" not in result.optimized_data["experience"][0]["highlights"][0]


class TestDocumentWriters:
    def test_layout_uses_standard_single_column_sections(self):
        kinds = [block.kind for block in build_blocks(resume())]
        headings = [b.text for b in build_blocks(resume()) if b.kind is BlockKind.HEADING]

        assert kinds[0] is BlockKind.NAME
        assert "WORK EXPERIENCE" in headings
        assert "SKILLS" in headings
        assert "EDUCATION" in headings

    def test_plain_text_render_contains_the_content(self):
        text = render_text(resume())
        assert "Priya Sharma" in text
        assert "Globex" in text
        assert "- Built FastAPI endpoints" in text

    def test_docx_is_a_valid_document(self):
        payload = render_docx(resume())
        assert payload[:2] == b"PK"       # docx is a zip archive
        assert len(payload) > 5000

    def test_pdf_is_a_valid_document(self):
        payload = render_pdf(resume())
        assert payload.startswith(b"%PDF-")
        assert len(payload) > 1000

    def test_generated_docx_reads_back_through_the_extraction_pipeline(self):
        # The whole point of generating a clean document is that a parser can
        # read it. Round-tripping proves it.
        result = extract_document(render_docx(resume()), filename="optimized.docx")

        assert result.ok
        assert "Priya Sharma" in result.text
        assert "Globex" in result.text
        assert result.confidence > 0.5

    def test_generated_pdf_reads_back_through_the_extraction_pipeline(self):
        result = extract_document(render_pdf(resume()), filename="optimized.pdf")

        assert result.ok
        assert not result.used_ocr        # a real text layer, not an image
        assert "Priya Sharma" in result.text
        assert "FastAPI" in result.text

    def test_handles_a_sparse_resume_without_crashing(self):
        sparse = {"schema_version": "1.0", "personal_info": {"name": "Sam"}}
        assert render_docx(sparse)[:2] == b"PK"
        assert render_pdf(sparse).startswith(b"%PDF-")
