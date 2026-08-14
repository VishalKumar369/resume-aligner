import json
from datetime import date
from pathlib import Path

import pytest

from app.schemas.structured import SCHEMA_VERSION, ResumeStructuredData
from app.services.extraction.pipeline import extract_document
from app.services.parsing.date_utils import (
    DateRange,
    find_date_range,
    strip_date_range,
    total_months,
)
from app.services.parsing.extractor_selector import ResumeExtractorSelector
from app.services.parsing.heuristic_resume_extractor import HeuristicResumeExtractor
from app.services.parsing.line_utils import merge_wrapped_lines, split_outside_parens
from app.services.parsing.llm_resume_extractor import LLMExtractionError, LLMResumeExtractor
from app.services.parsing.sections import Section, match_section_header, split_sections

UPLOADS_DIR = Path(__file__).resolve().parents[1] / "uploads"

SAMPLE_RESUME = """
Priya Sharma
Senior Data Engineer
priya.sharma@example.com | +91 98765 43210

PROFESSIONAL SUMMARY
Data engineer with a track record of building streaming pipelines and
mentoring junior engineers across distributed teams.

WORK EXPERIENCE
Globex Analytics Bengaluru, Karnataka
Senior Data Engineer March 2022 - Present
- Built a Kafka ingestion layer processing 2B events per day.
- Cut warehouse costs by 30% through partition pruning and
tiered storage.

Initech Remote
Data Engineering Intern June 2021 - November 2021
- Automated nightly reconciliation jobs in Python and Airflow.

EDUCATION
National Institute of Technology, Trichy Tiruchirappalli, Tamil Nadu
B.Tech in Information Technology August 2017 - May 2021
- Graduated with 8.7 CGPA.

SKILLS
Languages: Python, SQL, Scala
Platforms: AWS (EMR, S3), Databricks
Tools: Spark, Kafka, Docker, Kubernetes

PROJECTS
StreamGuard | github.com/priya/streamguard January 2023 - June 2023
Tech Stack: Python, Kafka, PostgreSQL
- Detected anomalies in event streams with a sliding-window model.

CERTIFICATIONS
AWS Certified Data Analytics - Specialty, 2023

ACHIEVEMENTS
- Speaker at PyCon India 2023 on streaming architectures.
"""


def _sample_pdf():
    pdfs = sorted(UPLOADS_DIR.glob("*.pdf")) if UPLOADS_DIR.exists() else []
    return pdfs[0] if pdfs else None


class FakeProvider:
    """Stands in for an AI provider so the LLM path is testable without a key."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    async def chat_completion(self, messages, temperature: float = 0.7, json_mode: bool = False):
        self.calls.append(messages)
        return self.responses.pop(0) if self.responses else ""

    async def generate_embedding(self, text):  # pragma: no cover - unused
        raise NotImplementedError


class TestDateUtils:
    def test_parses_month_year_range(self):
        found = find_date_range("Senior Data Engineer March 2022 - Present")
        assert found.as_iso() == ("2022-03", "present")
        assert found.is_current is True

    def test_parses_closed_range(self):
        assert find_date_range("Intern June 2021 - November 2021").as_iso() == ("2021-06", "2021-11")

    def test_parses_numeric_and_bare_year_ranges(self):
        assert find_date_range("Engineer 11/2021-07/2025").as_iso() == ("2021-11", "2025-07")
        assert find_date_range("Analyst 2019 to 2023").as_iso() == ("2019-01", "2023-01")

    def test_ignores_text_without_dates(self):
        assert find_date_range("Built a Kafka ingestion layer") is None

    def test_strips_the_range_leaving_the_role(self):
        assert strip_date_range("Associate Engineer, R&D February 2025 - Present") == "Associate Engineer, R&D"

    def test_overlapping_roles_are_not_double_counted(self):
        ranges = [
            DateRange(start=date(2020, 1, 1), end=date(2021, 12, 1)),
            DateRange(start=date(2020, 6, 1), end=date(2021, 12, 1)),
        ]
        assert total_months(ranges) == 24

    def test_consecutive_roles_form_one_stretch(self):
        ranges = [
            DateRange(start=date(2020, 1, 1), end=date(2020, 3, 1)),
            DateRange(start=date(2020, 4, 1), end=date(2020, 6, 1)),
        ]
        assert total_months(ranges) == 6

    def test_gap_between_roles_is_excluded(self):
        ranges = [
            DateRange(start=date(2018, 1, 1), end=date(2018, 6, 1)),
            DateRange(start=date(2020, 1, 1), end=date(2020, 6, 1)),
        ]
        assert total_months(ranges) == 12


class TestSections:
    def test_recognises_header_variants(self):
        assert match_section_header("WORK EXPERIENCE") is Section.EXPERIENCE
        assert match_section_header("Technical Skills") is Section.SKILLS
        assert match_section_header("Education") is Section.EDUCATION

    def test_content_line_is_not_a_header(self):
        assert match_section_header("Languages: Python, SQL") is None
        assert match_section_header("- Built a Kafka ingestion layer") is None

    def test_segments_a_resume(self):
        sections = split_sections(SAMPLE_RESUME)
        assert Section.EXPERIENCE in sections.found
        assert Section.SKILLS in sections.found
        assert "Globex Analytics Bengaluru, Karnataka" in sections.get(Section.EXPERIENCE)
        assert sections.get(Section.HEADER)[0] == "Priya Sharma"


class TestLineUtils:
    def test_rejoins_a_wrapped_bullet(self):
        merged = merge_wrapped_lines([
            "- Cut warehouse costs by 30% through partition pruning and",
            "tiered storage.",
        ])
        assert merged == ["- Cut warehouse costs by 30% through partition pruning and tiered storage."]

    def test_does_not_merge_a_new_entry_after_a_finished_sentence(self):
        merged = merge_wrapped_lines(["- Automated nightly jobs.", "Initech Remote"])
        assert len(merged) == 2

    def test_split_keeps_bracketed_commas_intact(self):
        assert split_outside_parens("AWS (EMR, S3), Databricks") == ["AWS (EMR, S3)", "Databricks"]


class TestHeuristicExtractor:
    @pytest.fixture(scope="class")
    def parsed(self):
        return HeuristicResumeExtractor().extract(SAMPLE_RESUME)

    def test_reads_personal_info(self, parsed):
        assert parsed.personal_info.name == "Priya Sharma"
        assert parsed.personal_info.title == "Senior Data Engineer"
        assert parsed.personal_info.email == "priya.sharma@example.com"
        assert parsed.personal_info.phone is not None

    def test_reads_experience_entries_with_real_fields(self, parsed):
        assert len(parsed.experience) == 2

        current = parsed.experience[0]
        assert current.company == "Globex Analytics"
        assert current.role == "Senior Data Engineer"
        assert current.location == "Bengaluru, Karnataka"
        assert current.start_date == "2022-03"
        assert current.end_date == "present"
        assert current.is_current is True
        assert current.is_internship is False
        assert len(current.highlights) == 2

    def test_flags_internships(self, parsed):
        internship = parsed.experience[1]
        assert internship.company == "Initech"
        assert internship.is_internship is True
        assert internship.duration_months == 6

    def test_computes_total_experience_from_dates(self, parsed):
        # Six months of internship plus an ongoing role since March 2022.
        assert parsed.total_experience_years > 3.0

    def test_reads_education(self, parsed):
        education = parsed.education[0]
        assert education.institution == "National Institute of Technology, Trichy"
        assert education.degree == "B.Tech in Information Technology"
        assert education.start_year == 2017
        assert education.end_year == 2021
        assert "8.7 CGPA" in (education.score or "")

    def test_reads_skill_categories(self, parsed):
        assert parsed.skills.categories["Languages"] == ["Python", "SQL", "Scala"]
        # A bracketed list must survive as one skill.
        assert "AWS (EMR, S3)" in parsed.skills.categories["Platforms"]
        assert "aws" in parsed.skills.normalized

    def test_does_not_invent_soft_skills(self, parsed):
        # The old parser returned the same three soft skills for everyone.
        assert "Mentoring" in parsed.skills.soft_skills
        assert "Leadership" not in parsed.skills.soft_skills

    def test_reads_projects_and_certifications(self, parsed):
        project = parsed.projects[0]
        assert project.name == "StreamGuard"
        assert project.tech_stack == ["Python", "Kafka", "PostgreSQL"]

        certification = parsed.certifications[0]
        assert certification.year == 2023
        assert certification.issuer == "AWS"

    def test_reads_achievements(self, parsed):
        assert parsed.achievements
        assert "PyCon India" in parsed.achievements[0]

    def test_reports_schema_version_and_confidence(self, parsed):
        assert parsed.schema_version == SCHEMA_VERSION
        assert parsed.extraction_meta["extractor"] == "heuristic"
        assert parsed.extraction_meta["confidence"] > 0.7

    def test_empty_text_yields_an_empty_but_valid_structure(self):
        parsed = HeuristicResumeExtractor().extract("")
        assert isinstance(parsed, ResumeStructuredData)
        assert parsed.experience == []
        assert parsed.total_experience_years == 0.0


@pytest.mark.skipif(_sample_pdf() is None, reason="no sample PDFs available")
class TestHeuristicExtractorOnRealPdf:
    @pytest.fixture(scope="class")
    def parsed(self):
        text = extract_document(_sample_pdf().read_bytes(), filename="resume.pdf").text
        return HeuristicResumeExtractor().extract(text)

    def test_recovers_contact_details(self, parsed):
        assert parsed.personal_info.name
        assert "@" in (parsed.personal_info.email or "")

    def test_recovers_dated_experience(self, parsed):
        assert parsed.experience
        assert all(entry.company for entry in parsed.experience)
        assert any(entry.start_date for entry in parsed.experience)

    def test_experience_years_is_no_longer_zero(self, parsed):
        # The old heuristic returned 0 for this resume.
        assert parsed.total_experience_years > 0

    def test_recovers_grouped_skills(self, parsed):
        assert parsed.skills.categories
        assert parsed.skills.hard_skills


class TestLLMExtractor:
    def _payload(self):
        return {
            "personal_info": {"name": "Priya Sharma", "email": "priya@example.com"},
            "summary": "Data engineer.",
            "skills": {"hard_skills": ["Python"], "soft_skills": [], "categories": {}},
            "experience": [{
                "company": "Globex",
                "role": "Senior Data Engineer",
                "start_date": "2022-03",
                "end_date": "present",
                "is_internship": False,
                "highlights": ["Built pipelines."],
            }],
            "education": [],
            "projects": [],
            "certifications": [],
            "achievements": [],
        }

    @pytest.mark.asyncio
    async def test_parses_a_clean_json_response(self):
        extractor = LLMResumeExtractor(provider=FakeProvider(json.dumps(self._payload())))
        parsed = await extractor.extract(SAMPLE_RESUME)

        assert parsed.personal_info.name == "Priya Sharma"
        assert parsed.extraction_meta["extractor"] == "llm"
        assert parsed.schema_version == SCHEMA_VERSION

    @pytest.mark.asyncio
    async def test_recovers_json_from_a_markdown_fence(self):
        fenced = f"Here you go:\n```json\n{json.dumps(self._payload())}\n```"
        extractor = LLMResumeExtractor(provider=FakeProvider(fenced))
        parsed = await extractor.extract(SAMPLE_RESUME)
        assert parsed.personal_info.name == "Priya Sharma"

    @pytest.mark.asyncio
    async def test_computes_durations_instead_of_trusting_the_model(self):
        extractor = LLMResumeExtractor(provider=FakeProvider(json.dumps(self._payload())))
        parsed = await extractor.extract(SAMPLE_RESUME)

        assert parsed.experience[0].is_current is True
        assert parsed.experience[0].duration_months > 0
        assert parsed.total_experience_years > 0

    @pytest.mark.asyncio
    async def test_retries_once_on_unparseable_output(self):
        provider = FakeProvider("not json at all", json.dumps(self._payload()))
        parsed = await LLMResumeExtractor(provider=provider).extract(SAMPLE_RESUME)

        assert parsed.personal_info.name == "Priya Sharma"
        assert len(provider.calls) == 2

    @pytest.mark.asyncio
    async def test_raises_when_output_never_becomes_valid(self):
        provider = FakeProvider("nope", "still nope")
        with pytest.raises(LLMExtractionError):
            await LLMResumeExtractor(provider=provider).extract(SAMPLE_RESUME)

    @pytest.mark.asyncio
    async def test_rejects_output_that_violates_the_schema(self):
        broken = {"experience": "should have been a list"}
        provider = FakeProvider(json.dumps(broken), json.dumps(broken))
        with pytest.raises(LLMExtractionError):
            await LLMResumeExtractor(provider=provider).extract(SAMPLE_RESUME)


class TestExtractorSelector:
    @pytest.mark.asyncio
    async def test_uses_the_heuristic_when_no_llm_is_configured(self):
        selector = ResumeExtractorSelector(prefer_llm=False)
        parsed = await selector.extract(SAMPLE_RESUME)

        assert parsed.extraction_meta["extractor"] == "heuristic"
        assert parsed.extraction_meta["fallback_used"] is False

    @pytest.mark.asyncio
    async def test_falls_back_to_the_heuristic_when_the_llm_fails(self):
        class ExplodingExtractor(LLMResumeExtractor):
            async def extract(self, text):
                raise RuntimeError("provider exploded")

        selector = ResumeExtractorSelector(llm=ExplodingExtractor(), prefer_llm=True)
        parsed = await selector.extract(SAMPLE_RESUME)

        # A dead provider must never fail the upload.
        assert parsed.extraction_meta["extractor"] == "heuristic"
        assert parsed.extraction_meta["fallback_used"] is True
        assert "provider exploded" in parsed.extraction_meta["fallback_reason"]
        assert parsed.personal_info.name == "Priya Sharma"

    @pytest.mark.asyncio
    async def test_prefers_the_llm_when_it_succeeds(self):
        payload = {
            "personal_info": {"name": "From LLM"},
            "skills": {"hard_skills": [], "soft_skills": [], "categories": {}},
            "experience": [], "education": [], "projects": [],
            "certifications": [], "achievements": [],
        }
        selector = ResumeExtractorSelector(
            llm=LLMResumeExtractor(provider=FakeProvider(json.dumps(payload))),
            prefer_llm=True,
        )
        parsed = await selector.extract(SAMPLE_RESUME)

        assert parsed.personal_info.name == "From LLM"
        assert parsed.extraction_meta["fallback_used"] is False

    @pytest.mark.asyncio
    async def test_empty_text_returns_a_valid_empty_structure(self):
        parsed = await ResumeExtractorSelector(prefer_llm=False).extract("   ")
        assert parsed.extraction_meta["extractor"] == "none"
        assert parsed.extraction_meta["confidence"] == 0.0
