import json

import pytest

from app.schemas.jd_structured import JD_SCHEMA_VERSION, JDStructuredData
from app.services.parsing.heuristic_jd_extractor import HeuristicJDExtractor
from app.services.parsing.jd_extractor_selector import JDExtractorSelector
from app.services.parsing.jd_sections import JDSection, match_jd_section_header, split_jd_sections
from app.services.parsing.llm_jd_extractor import LLMJDExtractionError, LLMJDExtractor

STRUCTURED_JD = """Senior Backend Engineer
Acme Technologies - Bengaluru, India (Hybrid)
Full-time

About the role
We are looking for a Senior Backend Engineer to own our payments platform.

Requirements
- 5+ years of experience building backend services
- Strong Python and FastAPI expertise
- Production experience with PostgreSQL and Redis
- Bachelor's degree in Computer Science or equivalent

Nice to have
- Kubernetes and Terraform
- Experience with Kafka

Responsibilities
- Design and own backend services end to end
- Mentor junior engineers
"""

UNSTRUCTURED_JD = """We need a Data Engineer to join our team in Pune.
You will build pipelines using Python and Spark on AWS.
Experience with Airflow is a nice to have.
"""


class FakeProvider:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    async def chat_completion(self, messages, temperature: float = 0.7, json_mode: bool = False):
        self.calls.append(messages)
        return self.responses.pop(0) if self.responses else ""

    async def generate_embedding(self, text):  # pragma: no cover - unused
        raise NotImplementedError


class TestJDSections:
    def test_recognises_requirement_and_preferred_headers(self):
        assert match_jd_section_header("Requirements") is JDSection.REQUIREMENTS
        assert match_jd_section_header("Nice to have") is JDSection.PREFERRED
        assert match_jd_section_header("What we're looking for") is JDSection.REQUIREMENTS

    def test_preferred_qualifications_beats_plain_qualifications(self):
        assert match_jd_section_header("Preferred Qualifications") is JDSection.PREFERRED
        assert match_jd_section_header("Minimum Qualifications") is JDSection.REQUIREMENTS

    def test_content_line_is_not_a_header(self):
        assert match_jd_section_header("- 5+ years of experience") is None

    def test_header_block_holds_the_title_and_company(self):
        sections = split_jd_sections(STRUCTURED_JD)
        assert sections.get(JDSection.HEADER)[0] == "Senior Backend Engineer"
        assert sections.has_requirement_sections is True

    def test_unstructured_posting_reports_no_requirement_sections(self):
        assert split_jd_sections(UNSTRUCTURED_JD).has_requirement_sections is False


class TestHeuristicJDExtractor:
    @pytest.fixture(scope="class")
    def parsed(self):
        return HeuristicJDExtractor().extract(STRUCTURED_JD)

    def test_reads_the_header_block(self, parsed):
        assert parsed.role == "Senior Backend Engineer"
        assert parsed.company == "Acme Technologies"
        assert parsed.location == "Bengaluru, India"
        assert parsed.work_mode == "hybrid"
        assert parsed.employment_type == "Full-Time"

    def test_separates_mandatory_from_preferred_skills(self, parsed):
        mandatory = parsed.requirements.mandatory_skills
        preferred = parsed.requirements.preferred_skills

        assert "Python" in mandatory
        assert "FastAPI" in mandatory
        assert "PostgreSQL" in mandatory

        # Nice-to-haves must not be scored as requirements.
        assert "Kubernetes" in preferred
        assert "Terraform" in preferred
        assert "Kafka" in preferred
        assert not set(mandatory) & set(preferred)

    def test_preferred_section_does_not_leak_cue_words_as_skills(self, parsed):
        # The old parser returned ["nice to have"] as the preferred skills.
        assert "nice to have" not in [skill.lower() for skill in parsed.requirements.preferred_skills]

    def test_reads_experience_and_seniority(self, parsed):
        assert parsed.min_experience_years == 5
        assert parsed.max_experience_years is None
        assert parsed.seniority == "senior"

    def test_reads_qualifications_and_responsibilities(self, parsed):
        assert any("Bachelor" in item for item in parsed.requirements.qualifications)
        assert parsed.responsibilities == [
            "Design and own backend services end to end",
            "Mentor junior engineers",
        ]

    def test_normalizes_skills_for_matching(self, parsed):
        assert "python" in parsed.requirements.normalized_mandatory
        assert "kubernetes" in parsed.requirements.normalized_preferred

    def test_reports_schema_version_and_scoping(self, parsed):
        assert parsed.schema_version == JD_SCHEMA_VERSION
        assert parsed.extraction_meta["skills_scoped_to_sections"] is True
        assert parsed.extraction_meta["confidence"] > 0.7

    def test_title_words_are_not_reported_as_skills_from_the_header(self):
        jd = "Senior React Engineer\nGlobex\n\nRequirements\n- Strong Python skills\n"
        parsed = HeuristicJDExtractor().extract(jd)

        # "React" appears only in the job title, never as a stated requirement.
        assert "Python" in parsed.requirements.mandatory_skills
        assert "React" not in parsed.requirements.mandatory_skills

    def test_falls_back_to_whole_body_when_there_are_no_sections(self):
        parsed = HeuristicJDExtractor().extract(UNSTRUCTURED_JD)

        assert "Python" in parsed.requirements.mandatory_skills
        assert "Spark" in parsed.requirements.mandatory_skills
        assert parsed.extraction_meta["skills_scoped_to_sections"] is False

    def test_cue_words_demote_a_skill_in_an_unstructured_posting(self):
        parsed = HeuristicJDExtractor().extract(UNSTRUCTURED_JD)

        # "Experience with Airflow is a nice to have."
        assert "Airflow" in parsed.requirements.preferred_skills
        assert "Airflow" not in parsed.requirements.mandatory_skills

    def test_extracts_a_role_from_a_hiring_cue_in_prose(self):
        parsed = HeuristicJDExtractor().extract(UNSTRUCTURED_JD)

        # "We need a Data Engineer to join our team in Pune."
        assert parsed.role == "Data Engineer"
        # No company is stated in this posting, so none is guessed.
        assert parsed.company is None

    def test_reads_labelled_role_and_company_lines(self):
        jd = (
            "Position: Machine Learning Engineer\n"
            "Company: Globex Corporation\n\n"
            "Requirements\n- 3+ years with Python and PyTorch\n"
        )
        parsed = HeuristicJDExtractor().extract(jd)

        assert parsed.role == "Machine Learning Engineer"
        assert parsed.company == "Globex Corporation"

    def test_reads_company_from_a_hiring_sentence(self):
        jd = (
            "Acme Labs is hiring engineers to scale our platform.\n\n"
            "Requirements\n- Strong Python and Go\n"
        )
        parsed = HeuristicJDExtractor().extract(jd)
        assert parsed.company == "Acme Labs"

    def test_reads_company_from_an_about_sentence(self):
        jd = (
            "Backend Engineer\n\n"
            "About Initech we build office software.\n\n"
            "Requirements\n- Java and Spring\n"
        )
        parsed = HeuristicJDExtractor().extract(jd)
        assert parsed.role == "Backend Engineer"
        assert parsed.company == "Initech"

    def test_about_the_role_is_not_read_as_a_company(self):
        jd = "Engineer\n\nAbout the role\nYou will build services.\n\nRequirements\n- Python\n"
        parsed = HeuristicJDExtractor().extract(jd)
        assert parsed.company is None

    def test_parses_a_bounded_experience_range(self):
        jd = "Engineer\n\nRequirements\n- 3-5 years of experience with Java\n"
        parsed = HeuristicJDExtractor().extract(jd)

        assert parsed.min_experience_years == 3
        assert parsed.max_experience_years == 5
        assert parsed.seniority == "mid"

    def test_counts_that_are_not_years_are_ignored(self):
        jd = "Engineer\n\nRequirements\n- Built 20+ REST APIs and 15+ services with Python\n"
        parsed = HeuristicJDExtractor().extract(jd)
        assert parsed.min_experience_years is None

    def test_empty_text_yields_a_valid_empty_structure(self):
        parsed = HeuristicJDExtractor().extract("")
        assert isinstance(parsed, JDStructuredData)
        assert parsed.requirements.mandatory_skills == []


class TestLLMJDExtractor:
    def _payload(self):
        return {
            "role": "Senior Backend Engineer",
            "company": "Acme Technologies",
            "location": "Bengaluru, India",
            "work_mode": "hybrid",
            "employment_type": "Full-time",
            "seniority": "senior",
            "min_experience_years": 5,
            "max_experience_years": None,
            "requirements": {
                "mandatory_skills": ["Python", "FastAPI"],
                "preferred_skills": ["Kubernetes", "Python"],
                "qualifications": ["Bachelor's degree"],
            },
            "responsibilities": ["Own backend services"],
        }

    @pytest.mark.asyncio
    async def test_parses_a_clean_json_response(self):
        extractor = LLMJDExtractor(provider=FakeProvider(json.dumps(self._payload())))
        parsed = await extractor.extract(STRUCTURED_JD)

        assert parsed.role == "Senior Backend Engineer"
        assert parsed.schema_version == JD_SCHEMA_VERSION
        assert parsed.extraction_meta["extractor"] == "llm"

    @pytest.mark.asyncio
    async def test_a_required_skill_is_not_also_preferred(self):
        extractor = LLMJDExtractor(provider=FakeProvider(json.dumps(self._payload())))
        parsed = await extractor.extract(STRUCTURED_JD)

        assert "Python" in parsed.requirements.mandatory_skills
        assert "Python" not in parsed.requirements.preferred_skills

    @pytest.mark.asyncio
    async def test_recovers_json_from_a_markdown_fence(self):
        fenced = f"```json\n{json.dumps(self._payload())}\n```"
        parsed = await LLMJDExtractor(provider=FakeProvider(fenced)).extract(STRUCTURED_JD)
        assert parsed.company == "Acme Technologies"

    @pytest.mark.asyncio
    async def test_retries_once_on_unparseable_output(self):
        provider = FakeProvider("not json", json.dumps(self._payload()))
        parsed = await LLMJDExtractor(provider=provider).extract(STRUCTURED_JD)

        assert parsed.role == "Senior Backend Engineer"
        assert len(provider.calls) == 2

    @pytest.mark.asyncio
    async def test_raises_when_output_never_becomes_valid(self):
        with pytest.raises(LLMJDExtractionError):
            await LLMJDExtractor(provider=FakeProvider("nope", "still nope")).extract(STRUCTURED_JD)

    @pytest.mark.asyncio
    async def test_rejects_output_that_violates_the_schema(self):
        broken = json.dumps({"responsibilities": "should have been a list"})
        with pytest.raises(LLMJDExtractionError):
            await LLMJDExtractor(provider=FakeProvider(broken, broken)).extract(STRUCTURED_JD)


class TestJDExtractorSelector:
    @pytest.mark.asyncio
    async def test_uses_the_heuristic_when_no_llm_is_configured(self):
        parsed = await JDExtractorSelector(prefer_llm=False).extract(STRUCTURED_JD)

        assert parsed.extraction_meta["extractor"] == "heuristic"
        assert parsed.extraction_meta["fallback_used"] is False

    @pytest.mark.asyncio
    async def test_falls_back_to_the_heuristic_when_the_llm_fails(self):
        class ExplodingExtractor(LLMJDExtractor):
            async def extract(self, text):
                raise RuntimeError("provider exploded")

        parsed = await JDExtractorSelector(llm=ExplodingExtractor(), prefer_llm=True).extract(STRUCTURED_JD)

        assert parsed.extraction_meta["extractor"] == "heuristic"
        assert parsed.extraction_meta["fallback_used"] is True
        assert parsed.role == "Senior Backend Engineer"

    @pytest.mark.asyncio
    async def test_empty_text_returns_a_valid_empty_structure(self):
        parsed = await JDExtractorSelector(prefer_llm=False).extract("  ")
        assert parsed.extraction_meta["extractor"] == "none"
