"""Recovering a company name from a posting URL (best-effort fallback)."""

import pytest

from app.services.parsing.jd_url import company_from_url


class TestCompanyFromUrl:
    @pytest.mark.parametrize(
        "url, expected",
        [
            ("https://apply.workable.com/writesonic/j/F057CDC530/", "Writesonic"),
            ("https://boards.greenhouse.io/stripe/jobs/12345", "Stripe"),
            ("https://jobs.lever.co/acme-corp/abc", "Acme Corp"),
            # A real company subdomain wins over the ATS path.
            ("https://acme.ashbyhq.com/roles/1", "Acme"),
            ("https://jobs.ashbyhq.com/writesonic/x", "Writesonic"),
            # A company's own careers page.
            ("https://careers.figma.com/jobs/eng", "Figma"),
            ("acme.com/careers", "Acme"),
        ],
    )
    def test_recovers_the_employer(self, url, expected):
        assert company_from_url(url) == expected

    @pytest.mark.parametrize(
        "url",
        [
            "https://www.linkedin.com/jobs/view/123",
            "https://www.indeed.com/viewjob?jk=abc",
            "https://www.glassdoor.com/job-listing/xyz",
            "",
            None,
            "not a url",
        ],
    )
    def test_returns_none_for_boards_and_junk(self, url):
        assert company_from_url(url) is None
