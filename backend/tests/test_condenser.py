"""Single-page condensing.

The condenser is driven by a fake page counter so these tests exercise the
trimming policy directly, without depending on exact PDF pagination. One test at
the end renders a real PDF to prove the policy actually reaches one page.
"""

import pytest

from app.services.documents.writers import count_pdf_pages
from app.services.optimization.condenser import SinglePageCondenser


def jd():
    return {
        "requirements": {
            "normalized_mandatory": ["python", "fastapi", "docker"],
            "normalized_preferred": ["kafka"],
        }
    }


def resume(highlights):
    return {
        "personal_info": {"name": "Priya Sharma", "email": "priya@example.com"},
        "skills": {"hard_skills": ["Python", "Docker"], "categories": {}},
        "experience": [
            {
                "company": "Globex",
                "role": "Backend Engineer",
                "highlights": list(highlights),
            }
        ],
    }


def bullets_of(data):
    return data["experience"][0]["highlights"]


class _PageStub:
    """Reports N pages until `keep` bullets remain across the resume, then 1."""

    def __init__(self, keep: int):
        self.keep = keep
        self.calls = 0

    def __call__(self, data) -> int:
        self.calls += 1
        total = sum(len(e.get("highlights") or []) for e in data.get("experience") or [])
        total += sum(len(p.get("highlights") or []) for p in data.get("projects") or [])
        return 1 if total <= self.keep else 2


class TestPolicy:
    def test_no_trim_when_already_one_page(self):
        data = resume(["Built FastAPI services.", "Shipped Docker images.", "Wrote docs.", "Filed reports."])
        condenser = SinglePageCondenser(page_counter=lambda d: 1)

        result = condenser.condense(data, jd())

        assert result.removed_bullets == 0
        assert result.fits is True
        assert len(bullets_of(data)) == 4

    def test_drops_the_least_relevant_bullet_first(self):
        # Two JD-relevant bullets, two irrelevant. Floor is 3, so exactly one
        # bullet may go - and it must be an irrelevant one.
        data = resume([
            "Built FastAPI services handling Docker workloads.",  # relevant
            "Organised the office party.",                        # irrelevant
            "Maintained Python data pipelines.",                  # relevant
            "Watered the plants weekly.",                         # irrelevant, longest-ish
        ])
        condenser = SinglePageCondenser(min_bullets_per_role=3, page_counter=_PageStub(keep=3))

        result = condenser.condense(data, jd())

        assert result.removed_bullets == 1
        assert result.fits is True
        remaining = bullets_of(data)
        assert "Built FastAPI services handling Docker workloads." in remaining
        assert "Maintained Python data pipelines." in remaining

    def test_prefers_the_longer_bullet_when_relevance_is_equal(self):
        data = resume([
            "Kept notes.",                                   # irrelevant, short
            "Coordinated cross-team scheduling logistics.",  # irrelevant, long
            "Shipped FastAPI endpoints.",                    # relevant
            "Ran Docker builds.",                            # relevant
        ])
        condenser = SinglePageCondenser(min_bullets_per_role=3, page_counter=_PageStub(keep=3))

        condenser.condense(data, jd())

        # The longer irrelevant bullet frees more space, so it goes first.
        assert "Coordinated cross-team scheduling logistics." not in bullets_of(data)
        assert "Kept notes." in bullets_of(data)

    def test_escalates_below_the_starting_floor_to_guarantee_one_page(self):
        # Only the first bullet is JD-relevant. Fits once a single bullet
        # remains, so the condenser must trim past the comfortable floor of 3.
        data = resume([
            "Built FastAPI services on Docker with Python.",  # relevant - kept
            "Filler one.", "Filler two.", "Filler three.", "Filler four.",
        ])
        condenser = SinglePageCondenser(min_bullets_per_role=3, page_counter=_PageStub(keep=1))

        result = condenser.condense(data, jd())

        assert result.fits is True
        assert len(bullets_of(data)) == 1
        assert "FastAPI" in bullets_of(data)[0]
        assert result.removed_bullets == 4

    def test_keeps_at_least_one_bullet_per_work_role(self):
        data = resume(["Only Python bullet.", "Two.", "Three."])
        # Never fits: proves experience is never gutted below one bullet.
        condenser = SinglePageCondenser(min_bullets_per_role=3, page_counter=lambda d: 2)

        result = condenser.condense(data, jd())

        assert len(bullets_of(data)) >= 1
        assert result.fits is False

    def test_reports_the_trim_as_a_change(self):
        data = resume(["A relevant Docker bullet.", "Filler one.", "Filler two.", "Filler three."])
        condenser = SinglePageCondenser(min_bullets_per_role=3, page_counter=_PageStub(keep=3))

        result = condenser.condense(data, jd())

        assert result.changes
        assert result.changes[0]["type"] == "condensed_single_page"
        assert "1" in result.changes[0]["description"]

    def test_trims_project_bullets_too(self):
        data = resume(["P", "F", "D"])  # experience at floor already
        data["projects"] = [
            {"name": "SiteWatch", "highlights": ["a", "b", "c", "d irrelevant filler bullet"]}
        ]
        # Fits after a single bullet is trimmed (6 bullets remain across the doc).
        condenser = SinglePageCondenser(min_bullets_per_role=3, page_counter=_PageStub(keep=6))

        result = condenser.condense(data, jd())

        assert result.removed_bullets == 1
        assert len(data["projects"][0]["highlights"]) == 3


class TestEscalation:
    """Beyond bullet trimming: dropping JD-irrelevant content to guarantee a page."""

    def test_drops_a_project_with_no_jd_relevance(self):
        data = resume(["P", "F", "D"])  # experience at floor
        data["projects"] = [
            {"name": "StreamGuard", "tech_stack": ["Python", "Docker"], "highlights": ["Built it."]},
            {"name": "Garden Blog", "tech_stack": ["Jekyll"], "highlights": ["Wrote posts."]},
        ]
        # Never fits by trimming (everything at floor), so it must drop content.
        # Stub fits only once the irrelevant project is gone.
        def counter(d):
            names = [p["name"] for p in d.get("projects") or []]
            return 1 if "Garden Blog" not in names else 2

        result = SinglePageCondenser(page_counter=counter).condense(data, jd())

        assert result.fits is True
        assert result.dropped_projects == 1
        names = [p["name"] for p in data["projects"]]
        assert names == ["StreamGuard"]  # the JD-relevant project survives

    def test_drops_the_summary_as_a_last_resort(self):
        data = resume(["Only Python.", "Two.", "Three."])
        data["summary"] = "A long professional summary paragraph about backend work."
        # Fits only once the summary is gone.
        counter = lambda d: 1 if not str(d.get("summary") or "").strip() else 2

        result = SinglePageCondenser(page_counter=counter).condense(data, jd())

        assert result.fits is True
        assert result.removed_summary is True
        assert data["summary"] == ""

    def test_prefers_trimming_bullets_over_dropping_a_project(self):
        # Gentle levers come first: a trimmable bullet goes before a whole
        # project is dropped.
        data = resume(["Python.", "F1", "F2", "F3", "F4"])
        data["projects"] = [{"name": "Side", "highlights": ["one"]}]
        condenser = SinglePageCondenser(min_bullets_per_role=3, page_counter=_PageStub(keep=5))

        result = condenser.condense(data, jd())

        assert result.removed_bullets == 1
        assert result.dropped_projects == 0
        assert len(data["projects"]) == 1


class TestAgainstRealRender:
    def test_condenses_a_long_resume_to_one_page(self):
        long_bullets = [
            f"Delivered production feature number {i} across services, "
            "coordinating rollout, monitoring, and documentation for the team."
            for i in range(40)
        ]
        data = resume(long_bullets)
        assert count_pdf_pages(data) > 1, "fixture should start as multi-page"

        result = SinglePageCondenser(min_bullets_per_role=3).condense(data, jd())

        assert result.fits is True
        assert result.page_count == 1
        assert result.removed_bullets > 0
        # A work role always keeps at least one bullet.
        assert len(bullets_of(data)) >= 1

    def test_guarantees_one_page_for_a_heavy_multi_section_resume(self):
        # Several roles, many projects, a summary - the kind of resume that
        # overflows. Single page must still be guaranteed.
        data = {
            "personal_info": {"name": "Priya Sharma", "email": "priya@example.com",
                              "phone": "+91 98765 43210", "location": "Bengaluru"},
            "summary": "Backend engineer with a long and detailed professional summary "
                       "spanning several lines about services, scale, and reliability work.",
            "skills": {"hard_skills": ["Python", "FastAPI", "Docker", "Kafka"], "categories": {}},
            "experience": [
                {
                    "company": f"Company {r}", "role": "Backend Engineer",
                    "start_date": "2019", "end_date": "2024",
                    "highlights": [
                        f"Delivered feature {i} with rollout, monitoring, and docs for the team."
                        for i in range(8)
                    ],
                }
                for r in range(4)
            ],
            "projects": [
                {"name": f"Project {p}", "tech_stack": ["Go"],
                 "highlights": [f"Built component {i} end to end." for i in range(4)]}
                for p in range(4)
            ],
            "education": [{"degree": "B.Tech", "institution": "NIT", "start_year": 2015, "end_year": 2019}],
            "achievements": ["Spoke at a conference.", "Won an internal hackathon."],
        }
        assert count_pdf_pages(data) > 1

        result = SinglePageCondenser(min_bullets_per_role=3).condense(data, jd())

        assert result.fits is True
        assert result.page_count == 1
        # Every work role survives with at least one bullet.
        assert all(len(e["highlights"]) >= 1 for e in data["experience"])
        assert len(data["experience"]) == 4
