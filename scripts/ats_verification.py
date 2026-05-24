"""ATS posting verification — deep liveness checks beyond HTTP status codes.

Some companies (e.g., Cursor) list jobs on Ashby's API index but host their
own application forms on native career pages.  Ashby returns HTTP 200 for
the posting page while rendering a client-side "Page not found" because the
``__appData`` JSON has ``"posting": null``.

This module provides:
- ``verify_ashby_posting_live(url)`` — True only if the posting data exists
- ``NATIVE_CAREER_PAGES`` — mapping of companies that host their own forms
- ``resolve_application_url(entry)`` — returns the correct apply URL
- ``verify_posting_accepts_applications(entry)`` — full verification
"""

from __future__ import annotations

import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

HTTP_TIMEOUT = 12

# ─── Companies that host application forms on their own domain ───────────
# Key: lowercased org name matching pipeline YAML target.organization
# Value: template for building the application URL from the Ashby job slug
#        {slug} is derived from the Ashby job title (kebab-cased)
NATIVE_CAREER_PAGES: dict[str, str] = {
    "cursor": "https://www.cursor.com/careers/{slug}",
}


def _ashby_slug_from_title(title: str) -> str:
    """Convert an Ashby job title to a URL slug matching native career pages.

    'Software Engineer, Enterprise Platform' → 'software-engineer-enterprise-platform'
    """
    slug = title.lower()
    slug = re.sub(r"[,/&]+", " ", slug)
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    slug = re.sub(r"-+", "-", slug)
    return slug


def _ashby_slug_from_url(url: str) -> str | None:
    """Extract the Ashby posting ID from a URL for diagnostic purposes."""
    m = re.search(r"jobs\.ashbyhq\.com/[^/]+/([a-f0-9-]+)", url)
    return m.group(1) if m else None


def verify_ashby_posting_live(url: str) -> bool:
    """Check if an Ashby posting actually accepts applications.

    Ashby returns HTTP 200 for all posting URLs, but dead postings have
    ``"posting":null`` in the ``__appData`` JSON embedded in the HTML.
    This function does a deep check beyond HTTP status codes.

    Returns True if the posting is accepting applications, False otherwise.
    """
    if not url or "ashbyhq.com" not in url:
        return True  # Not Ashby — skip

    # Ensure we're hitting the application page
    check_url = url.rstrip("/")
    if not check_url.endswith("/application"):
        check_url += "/application"

    try:
        req = Request(check_url, headers={"User-Agent": "application-pipeline/1.0"})
        with urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError, TimeoutError, OSError):
        return False  # Can't reach it — assume dead

    # Check the __appData JSON for posting data
    m = re.search(r'window\.__appData\s*=\s*(\{.*?\});', body)
    if not m:
        return False  # Can't parse — assume dead

    try:
        app_data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return False

    # If posting is null, the job doesn't accept applications here
    return app_data.get("posting") is not None


def resolve_application_url(entry: dict) -> str:
    """Resolve the correct application URL for an entry.

    For companies with native career pages, converts the Ashby URL to the
    company's own application URL.  For all others, returns the existing URL.
    """
    target = entry.get("target", {})
    if not isinstance(target, dict):
        return ""

    org = (target.get("organization") or "").lower()
    app_url = target.get("application_url", "")
    portal = target.get("portal", "")

    # Already resolved to a native page?
    if portal not in ("ashby", "") or "ashbyhq.com" not in app_url:
        return app_url

    # Check if this company has native career pages
    template = NATIVE_CAREER_PAGES.get(org)
    if not template:
        return app_url

    # Derive slug from entry name or title
    name = entry.get("name", "")
    # Strip company prefix: "Cursor Software Engineer, Enterprise Platform" → "Software Engineer, Enterprise Platform"
    org_title = target.get("organization", "")
    if name.startswith(org_title):
        title = name[len(org_title):].strip()
    else:
        title = name

    slug = _ashby_slug_from_title(title)
    return template.format(slug=slug)


def verify_posting_accepts_applications(entry: dict) -> tuple[bool, str]:
    """Full verification that an entry's posting accepts applications.

    Returns (is_live, reason).
    - (True, "live") — posting is accepting applications
    - (True, "native") — redirected to native career page
    - (False, "posting_null") — Ashby posting data is null
    - (False, "unreachable") — could not reach the posting
    """
    target = entry.get("target", {})
    if not isinstance(target, dict):
        return False, "no_target"

    app_url = target.get("application_url", "")
    portal = target.get("portal", "")

    if not app_url:
        return False, "no_url"

    # Non-Ashby portals: just check HTTP liveness
    if portal not in ("ashby",) and "ashbyhq.com" not in app_url:
        return True, "non_ashby"

    # Check native career page mapping first
    org = (target.get("organization") or "").lower()
    if org in NATIVE_CAREER_PAGES:
        native_url = resolve_application_url(entry)
        if native_url and native_url != app_url:
            # Verify the native URL is reachable
            try:
                req = Request(native_url, method="HEAD",
                              headers={"User-Agent": "application-pipeline/1.0"})
                with urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                    if resp.getcode() and 200 <= resp.getcode() < 400:
                        return True, "native"
            except (HTTPError, URLError, TimeoutError, OSError):
                pass

    # Deep Ashby verification
    if verify_ashby_posting_live(app_url):
        return True, "live"

    return False, "posting_null"
