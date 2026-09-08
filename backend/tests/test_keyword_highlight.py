"""Building and applying the JD-keyword highlight pattern."""

from app.services.documents.keyword_highlight import (
    compile_keyword_pattern,
    jd_keywords,
    segment_text,
)


def _bold(text: str, *keywords: str):
    pattern = compile_keyword_pattern(keywords)
    return [chunk for chunk, is_keyword in segment_text(text, pattern) if is_keyword]


class TestKeywordPattern:
    def test_does_not_match_a_keyword_inside_a_longer_word(self):
        # "Java" must not light up inside "JavaScript".
        assert _bold("Built with JavaScript", "Java") == []
        assert _bold("Built with JavaScript and Java", "Java", "JavaScript") == ["JavaScript", "Java"]

    def test_prefers_the_longest_matching_term(self):
        assert _bold("Designed REST API endpoints", "API", "REST API") == ["REST API"]

    def test_matches_symbol_tech_tokens_whole(self):
        # "C++" is one token; a bare "C" is dropped as too short/ambiguous.
        assert _bold("Wrote C++ code, not C", "C++", "C") == ["C++"]
        assert _bold("Shipped .NET and Node.js services", ".NET", "Node.js") == [".NET", "Node.js"]

    def test_is_case_insensitive(self):
        assert _bold("strong python skills", "Python") == ["python"]

    def test_empty_or_trivial_keywords_compile_to_none(self):
        assert compile_keyword_pattern([]) is None
        assert compile_keyword_pattern(["", " ", "a"]) is None  # <2 chars dropped

    def test_segment_without_a_pattern_returns_the_text_whole(self):
        assert segment_text("anything", None) == [("anything", False)]


class TestJdKeywords:
    def test_collects_mandatory_and_preferred_skills(self):
        jd = {
            "requirements": {
                "mandatory_skills": ["Python", "FastAPI"],
                "preferred_skills": ["Kafka"],
            }
        }
        assert jd_keywords(jd) == ["Python", "FastAPI", "Kafka"]

    def test_missing_requirements_yield_no_keywords(self):
        assert jd_keywords({}) == []
        assert compile_keyword_pattern(jd_keywords({})) is None
