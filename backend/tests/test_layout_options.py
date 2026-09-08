"""Section reorder / include-exclude and the selectable template layouts."""

from app.services.documents.layout import BlockKind, build_blocks
from app.services.documents.writers import LAYOUT_IDS, render_docx, render_pdf

RESUME = {
    "personal_info": {"name": "V K", "email": "v@x.com"},
    "summary": "Backend engineer.",
    "skills": {"categories": {"Languages": ["Python"]}},
    "experience": [{"role": "Eng", "company": "Acme", "highlights": ["Built APIs"]}],
    "education": [{"degree": "B.Tech", "institution": "IIIT"}],
    "achievements": ["Solved 500+ problems"],
}


def _headings(section_order=None):
    return [b.text for b in build_blocks(RESUME, section_order) if b.kind is BlockKind.HEADING]


class TestSectionOrder:
    def test_default_order_includes_every_section(self):
        assert _headings() == [
            "PROFESSIONAL SUMMARY", "SKILLS", "WORK EXPERIENCE", "EDUCATION", "ACHIEVEMENTS"
        ]

    def test_reorders_and_excludes_sections(self):
        # Achievements moved up; skills and education dropped.
        assert _headings(["summary", "achievements", "experience"]) == [
            "PROFESSIONAL SUMMARY", "ACHIEVEMENTS", "WORK EXPERIENCE"
        ]

    def test_unknown_keys_are_ignored(self):
        assert _headings(["experience", "bogus"]) == ["WORK EXPERIENCE"]

    def test_empty_order_falls_back_to_the_default(self):
        # An all-unknown/empty list must not produce a bodyless resume.
        assert _headings([]) == _headings(None)

    def test_a_named_but_absent_section_renders_nothing(self):
        thin = {"personal_info": {"name": "V K"}, "experience": [
            {"role": "Eng", "company": "Acme", "highlights": ["Did work"]}]}
        heads = [b.text for b in build_blocks(thin, ["summary", "experience"]) if b.kind is BlockKind.HEADING]
        assert heads == ["WORK EXPERIENCE"]


class TestHighlighting:
    def test_bolds_jd_keywords_in_skills_and_summary_not_only_bullets(self):
        import io

        import docx

        from app.services.documents.keyword_highlight import compile_keyword_pattern

        data = {
            "personal_info": {"name": "V K"},
            "summary": "Ships features in Python every week.",
            "skills": {"categories": {"Languages": ["Python", "Java"]}},
            "experience": [{"company": "Acme", "role": "Eng", "highlights": ["Built with Python"]}],
        }
        pattern = compile_keyword_pattern(["Python"])
        document = docx.Document(io.BytesIO(render_docx(data, pattern, "professional")))

        # "Python" is bold in the summary, the skills line, and the bullet — not
        # just bullets. (Uppercase heading paragraphs are excluded.)
        bold_paras = [
            p for p in document.paragraphs
            if not p.text.isupper() and any(r.bold and r.text.strip(",") == "Python" for r in p.runs)
        ]
        assert len(bold_paras) >= 2


class TestLayouts:
    def test_every_layout_renders_docx_and_pdf(self):
        for layout in LAYOUT_IDS:
            docx = render_docx(RESUME, None, layout)
            pdf = render_pdf(RESUME, None, layout)
            assert len(docx) > 0
            assert pdf[:4] == b"%PDF"

    def test_an_unknown_layout_falls_back_to_classic(self):
        assert render_docx(RESUME, None, "does-not-exist")  # no crash, renders
