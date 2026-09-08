"""Recover a company name from a job-posting URL.

The app never fetches the link (it is saved for reference only), but the URL
string itself usually names the employer: applicant-tracking systems put the
company in the path (workable.com/<company>/…) or a subdomain
(<company>.ashbyhq.com), and a company's own careers page sits on its domain
(careers.<company>.com). This is a best-effort fallback used only when the JD
text yields no company, so it stays conservative and returns None when unsure.
"""

import re
from typing import Optional
from urllib.parse import urlparse

# ATS hosts that carry the employer's slug in the URL.
_ATS_HOSTS = (
    "workable.com", "greenhouse.io", "lever.co", "ashbyhq.com",
    "smartrecruiters.com", "recruitee.com", "breezy.hr", "teamtailor.com",
    "jobvite.com", "icims.com", "myworkdayjobs.com", "bamboohr.com",
    "personio.com", "join.com", "pinpointhq.com", "rippling.com",
)

# Job boards and aggregators: the URL names the board, not the employer.
_JOB_BOARDS = (
    "linkedin.com", "indeed.com", "glassdoor.com", "naukri.com", "monster.com",
    "ziprecruiter.com", "wellfound.com", "angel.co", "dice.com", "google.com",
    "bing.com", "simplyhired.com", "flexjobs.com", "remoteok.com", "weworkremotely.com",
)

# Subdomains that name the ATS/section, not the employer.
_GENERIC_SUBDOMAINS = frozenset({
    "apply", "apply2", "boards", "board", "jobs", "job", "careers", "career",
    "www", "secure", "app", "hire", "hiring", "recruiting", "talent", "work",
})

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,39}$")


def _humanize(slug: str) -> Optional[str]:
    words = [w for w in re.split(r"[-_]+", slug) if w]
    if not words:
        return None
    # Keep short all-letter tokens uppercased (e.g. "ibm" -> "IBM") only when
    # very short; otherwise title-case each word.
    out = []
    for w in words:
        out.append(w.upper() if len(w) <= 3 and w.isalpha() else w.capitalize())
    return " ".join(out)


def _slug_ok(segment: str) -> bool:
    seg = (segment or "").lower()
    return bool(_SLUG_RE.match(seg)) and not seg.isdigit()


def company_from_url(url: Optional[str]) -> Optional[str]:
    if not url or not str(url).strip():
        return None
    try:
        parsed = urlparse(url if "://" in url else f"https://{url}")
    except ValueError:
        return None

    host = (parsed.hostname or "").lower().lstrip(".")
    if not host:
        return None
    if any(host == b or host.endswith("." + b) for b in _JOB_BOARDS):
        return None

    labels = host.split(".")
    subdomain = labels[0] if len(labels) > 2 else ""
    path_parts = [seg for seg in parsed.path.split("/") if seg]

    if any(host == h or host.endswith("." + h) for h in _ATS_HOSTS):
        # A real company subdomain is authoritative: <company>.ashbyhq.com,
        # <company>.breezy.hr. Generic subdomains (apply/boards/jobs/…) instead
        # carry the company as the first path segment: workable.com/<company>/…
        if subdomain and subdomain not in _GENERIC_SUBDOMAINS and _slug_ok(subdomain):
            return _humanize(subdomain)
        if path_parts and _slug_ok(path_parts[0]):
            return _humanize(path_parts[0])
        return None

    # A company's own site: careers.acme.com / acme.com/careers -> "Acme".
    registrable = labels[-2] if len(labels) >= 2 else labels[0]
    if _slug_ok(registrable):
        return _humanize(registrable)
    return None
